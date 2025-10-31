"""Solrizer web application.

This web application is built using the [Flask](https://flask.palletsprojects.com/)
framework.

## Configuration

Configuration of the application is handled by a combination of
[environment variables](#environment) and [configuration files](#files).

### Environment

#### fcrepo Repository

* **`SOLRIZER_FCREPO_ENDPOINT`** URL of the fcrepo repository.
* **`SOLRIZER_FCREPO_JWT_SECRET`** Shared secret used to generate
  access tokens to connect to the fcrepo repository.

#### Handle Server

* **`SOLRIZER_HANDLE_PROXY_PREFIX`** HTTP URL of the handle service
  resolver that should be prepended to a handle to make a resolvable
  URL. See the `solrizer.indexers.handles` indexer for more information
  about the handles indexer.

#### IIIF

* **`SOLRIZER_IIIF_IDENTIFIER_PREFIX`** Prefix to use when generating
  IIIF identifiers from repository URIs. See the `solrizer.indexers.iiif_links`
  indexer module for more information about the IIIF indexer.
* **`SOLRIZER_IIIF_MANIFESTS_URL_PATTERN`** URL template for IIIF manifests.
  Use `{+id}` to insert the IIIF identifier of the top-level object.
* **`SOLRIZER_IIIF_THUMBNAIL_URL_PATTERN`** URL template for IIIF image server
  URLs for individual thumbnail images. Use `{+id}` to insert the IIIF
  identifier for the image.

#### Indexers

* **`SOLRIZER_INDEXERS_FILE`** Name of the file listing which
  indexers to use for each content model.
* **`SOLRIZER_INDEXER_SETTINGS_FILE`** Name of the file that
  contains indexer-specific configuration.

#### Plastron Client Caching

* **`SOLRIZER_PLASTRON_CACHE_ENABLED`** Whether to use client caching in the
  Plastron client connecting to the fcrepo repository. Defaults to `False`.
* **`SOLRIZER_PLASTRON_CACHE_NAME`** Value for the `cache_name` of the
  [requests-cache](https://requests-cache.readthedocs.io/) `CachedSession`.
  Defaults to `solrizer_cache`.
* **`SOLRIZER_PLASTRON_CACHE_BACKEND`** String alias for the cache backend
  to use. Defaults to `None`, which in turn falls back to the default
  defined by [requests-cache](https://requests-cache.readthedocs.io/), which
  is currently `SQLiteCache`.
* **`SOLRIZER_PLASTRON_CACHE_PARAMS`** Mapping of optional additional parameters
  to pass to the cache backend, formatted as a JSON object (e.g.,
  `{"host":"localhost","port":6379}`)
* **`SOLRIZER_PLASTRON_CACHE_EXPIRE_AFTER`** Cache expiration time in seconds.
  Defaults to `120`.

See also the `get_session()` function.

#### Solr Server

* **`SOLRIZER_SOLR_QUERY_ENDPOINT`** URL of the Solr service to query for
  the current document for a given item. This is required to generate the
  atomic updates for `?command=update` query parameter. See also the
  `solrizer.solr.create_atomic_update()` function.

During development, it is also useful to set `FLASK_DEBUG=1` to enable
Flask's debug mode, which includes detailed error pages, `DEBUG`-level
logging, and hot reloading when the source code is updated.

Once the above `SOLRIZER_*` environment variables are loaded, they are available
from the Flask app's `config` object without the `SOLRIZER_` prefix.

```
# in a .env file:
SOLRIZER_FCREPO_ENDPOINT=http://localhost:8080/fcrepo/rest

# in Python code:
app.config['FCREPO_ENDPOINT']  # 'http://localhost:8080/fcrepo/rest'
```

### Files

Files may be in YAML or JSON format, with the suffixes ".yml"/".yaml" or
".json", respectively. Their contents here are described in terms of the
Python data structures that are deserialized from them. See the
`load_config_from_files()` function for more details.

* **Indexers file (`SOLRIZER_INDEXERS_FILE`)** Dictionary of Plastron
  content model names to lists of indexers that should be run for objects
  with that content model.

  If no entry for a content model is found, the system looks for a
  `__default__` entry instead. If that is not found, it uses the
  hardcoded default of just the `solrizer.indexers.content_model`
  indexer.

* **Indexer settings file (`SOLRIZER_INDEXER_SETTINGS_FILE`)** Dictionary
  of indexer names to settings for that particular indexer. See the
  individual indexer modules for a description of what setting they support.

---
"""

import json
import logging
import os
from collections.abc import Mapping, MutableMapping
from datetime import datetime
from pathlib import Path
from time import strftime
from typing import Any

import psutil
import yaml
from codetiming import Timer
from flask import Flask, request
from plastron.client import Client, Endpoint
from plastron.models import ModelClassError, guess_model
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryError, RepositoryResource
from plastron.utils import envsubst
from requests import Session
from requests_cache import CachedSession, init_backend
from requests_jwtauth import JWTSecretAuth
from werkzeug.exceptions import InternalServerError

from solrizer import __version__
from solrizer.errors import (
    NoResourceRequested,
    ProblemDetailError,
    ResourceNotAvailable,
    UnknownCommand,
    problem_detail_response, ConfigurationError,
)
from solrizer.indexers import IndexerContext, IndexerError
from solrizer.solr import create_atomic_update

debug_mode = int(os.environ.get('FLASK_DEBUG', '0'))
logging.basicConfig(
    level='DEBUG' if debug_mode else 'INFO',
    format='%(levelname)s:%(threadName)s:%(name)s:%(message)s',
)
logger = logging.getLogger(__name__)

LOADERS = {
    '.json': json.load,
    '.yml': yaml.safe_load,
    '.yaml': yaml.safe_load,
}


def load_config_from_files(config: MutableMapping):
    """Iterates over the keys in `config`. For any with the format "{NAME}_FILE",
    treat its value as a filename. Reads that file using the appropriate loader
    (".json" files use `json.load`, and ".yml" and ".yaml" files use `yaml.safe_load`)
    and set the config key "{NAME}" to the return value of the loader.

    After loading, uses `plastron.utils.envsubst` to apply substitutions to the
    loaded object. You may use any of the keys currently defined in the config;
    in particular, this means you can use the values of environment variables
    with the prefix `SOLRIZER_`. In the file, use the name without the `SOLRIZER_`
    prefix.

    ```zsh
    # environment
    SOLRIZER_HANDLE_PROXY_PREFIX=http://hdl-local/
    SOLRIZER_INDEXER_SETTINGS_FILE=indexer-settings.yml
    ```

    ```yaml
    # indexer-settings.yml
    handles:
      proxy_prefix: ${HANDLE_PROXY_PREFIX}
    ```

    Results in this value for `config['INDEXER_SETTINGS']`:

    ```python
    {
        'handles': {
            'proxy_prefix': 'http://hdl-local/'
        }
    }
    ```

    Ignores a "{NAME}_FILE" key if "{NAME}" is already defined in config (i.e.,
    "{NAME}" takes precedence over "{NAME}_FILE").

    Raises a `RuntimeError` if the file suffix is unrecognized, or if the file
    cannot be opened."""
    file_keys = [k for k in config.keys() if k.endswith('_FILE')]
    for file_key in file_keys:
        # strip the "_FILE" suffix
        key = file_key[:-5]
        if key not in config:
            # only load from file if there isn't already a config value with this key
            file = Path(config[file_key])
            try:
                loader = LOADERS[file.suffix]
            except KeyError as e:
                raise RuntimeError(f'Cannot open a config file with suffix "{file.suffix}"') from e
            try:
                with file.open() as fh:
                    config[key] = envsubst(loader(fh), config)
            except FileNotFoundError as e:
                raise RuntimeError(f'Config file "{file}" not found') from e


def get_session(config: Mapping[str, Any]) -> Session:
    """Creates a [Session](https://requests.readthedocs.io/en/latest/api/#request-sessions)
    or [CachedSession](https://requests-cache.readthedocs.io/en/stable/modules/requests_cache.session.html)
    object from the given configuration.

    Recognized keys in `config` are:

    * `PLASTRON_CACHE_ENABLED`
    * `PLASTRON_CACHE_NAME`
    * `PLASTRON_CACHE_BACKEND`
    * `PLASTRON_CACHE_PARAMS`
    * `PLASTRON_CACHE_EXPIRES_AFTER`

    See [Environment Variables § Plastron Client Caching](#plastron-client-caching)
    for more details about the usage of each of these. Note that in the environment
    variables section, they are all prefixed with `SOLRIZER_`.
    """
    if config.get('PLASTRON_CACHE_ENABLED', False):
        logger.info('Plastron client caching enabled')
        backend = init_backend(
            cache_name=config.get('PLASTRON_CACHE_NAME', 'solrizer_cache'),
            backend=config.get('PLASTRON_CACHE_BACKEND'),
            **config.get('PLASTRON_CACHE_PARAMS', {}),
        )
        return CachedSession(
            backend=backend,
            expire_after=config.get('PLASTRON_CACHE_EXPIRE_AFTER', 120),
        )
    else:
        return Session()


def create_app():
    start_time = datetime.now()
    app = Flask(__name__)
    app.config.from_prefixed_env('SOLRIZER')
    load_config_from_files(app.config)

    client = Client(
        endpoint=Endpoint(app.config['FCREPO_ENDPOINT']),
        auth=JWTSecretAuth(
            secret=app.config['FCREPO_JWT_SECRET'], claims={'sub': 'solrizer', 'iss': 'solrizer', 'role': 'fedoraAdmin'}
        ),
        session=get_session(app.config),
    )
    app.config['repo'] = Repository(client=client)
    app.config['INDEXERS'] = app.config.get('INDEXERS', {})
    if '__default__' not in app.config['INDEXERS']:
        app.config['INDEXERS']['__default__'] = ['content_model']

    # Source: https://gist.github.com/alexaleluia12/e40f1dfa4ce598c2e958611f67d28966
    @app.after_request
    def after_request(response):
        timestamp = strftime('[%Y-%m-%d %H:%M]')
        logger.info('%s %s %s %s %s', timestamp, request.method, request.scheme, request.full_path, response.status)
        return response

    @app.route('/')
    def root():
        return f'''
        <html>
          <head>
            <title>Solrizer</title>
          </head>
          <body>
            <h1>Solrizer</h1>
            <form method="get" action="/doc">
              <label>URI: <input name="uri" type="text" size="80"/></label>
              <select name="command">
                <option value=""></option>
                <option value="add">add</option>
                <option value="update">update</option>
              </select>
              <button type="submit">Submit</button>
            </form>
            <hr/>
            <p id="version">{__version__}</p>
          </body>
        </html>
        '''

    @app.route('/health')
    def get_health():
        uptime = datetime.now() - start_time
        memory = psutil.virtual_memory()
        status = {
            'status': 'ok',
            'uptime': str(uptime),
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'used_percent': memory.percent,
            },
        }
        logger.info(f'Health: {status}')
        return status

    @app.route('/doc')
    def get_doc():
        uri = request.args.get('uri')

        if uri is None:
            raise NoResourceRequested()

        command = request.args.get('command', None)
        if command not in ('add', 'update', '', None):
            raise UnknownCommand(value=command)
        if command == 'update' and 'SOLR_QUERY_ENDPOINT' not in app.config:
            app.logger.error('The "update" command requires SOLRIZER_SOLR_QUERY_ENDPOINT to be set')
            raise ConfigurationError()

        with Timer(
            name=f'create Solr document for {uri}',
            text='Time to {name}: {milliseconds:.3f} ms',
            logger=app.logger.info,
        ):
            try:
                resource: RepositoryResource = app.config['repo'][uri].read()
            except RepositoryError as e:
                raise ResourceNotAvailable(uri=uri) from e

            # dynamically determine the model_class
            try:
                model_class = guess_model(resource.describe(RDFResource))
            except ModelClassError as e:
                app.logger.error(f'Unable to determine model class for {uri}')
                raise ResourceNotAvailable(uri=uri) from e

            logger.info(f'Model class for {uri} is {model_class.__name__}')

            ctx = IndexerContext(
                repo=app.config['repo'],
                resource=resource,
                model_class=model_class,
                doc={'id': uri},
                config=app.config,
            )
            try:
                indexers = app.config['INDEXERS'][model_class.__name__]
            except KeyError as e:
                logger.info(f'No specific indexers configured for the {e} model, using defaults')
                indexers = app.config['INDEXERS']['__default__']

            logger.info(f'Running indexers: {indexers}')
            try:
                doc = ctx.run(indexers)
            except (IndexerError, RuntimeError) as e:
                app.logger.error(f'Error while processing {uri} for indexing: {e}')
                raise InternalServerError(f'Error while processing {uri} for indexing: {e}')

            match command:
                case 'add':
                    # wrap in an add command
                    doc = {"add": {"doc": doc}}
                case 'update':
                    # create an atomic update by comparing the newly generated document to
                    # the existing document in Solr for the given item
                    try:
                        doc = [create_atomic_update(doc, app.config['SOLR_QUERY_ENDPOINT'])]
                    except KeyError as e:
                        raise InternalServerError('Cannot generate Solr atomic update') from e
                case None, '':
                    # just the plain document
                    pass

            return json.dumps(doc, sort_keys=True), {'Content-Type': 'application/json;charset=utf-8'}

    # serve error responses using the RFC 9457 Problem Detail JSON format
    app.register_error_handler(ProblemDetailError, problem_detail_response)

    return app

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
from collections.abc import Mapping
from datetime import datetime
from time import strftime
from typing import Any

import psutil
import yaml
from codetiming import Timer
from configurenv import load_config_from_files
from flask import Flask, render_template, request
from plastron.client import Client, Endpoint
from plastron.client.proxied import ProxiedClient
from plastron.models import ModelClassError, guess_model
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryError, RepositoryResource
from requests import Session
from requests.auth import AuthBase
from requests_cache import CachedSession, init_backend
from requests_jwtauth import JWTSecretAuth
from solrizer import __version__
from solrizer.errors import (
    ConfigurationError,
    NoResourceRequested,
    ProblemDetailError,
    ResourceNotAvailable,
    UnknownCommand,
    BadIndexersParameter,
    problem_detail_response,
)
from solrizer.indexers import AVAILABLE_INDEXERS, IndexerContext, IndexerError
from solrizer.solr import create_atomic_update
from werkzeug.exceptions import InternalServerError

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


def get_authenticator(config: Mapping[str, Any]) -> AuthBase | None:
    if 'FCREPO_JWT_SECRET' not in config:
        return None

    return JWTSecretAuth(
        secret=config['FCREPO_JWT_SECRET'],
        claims={'sub': 'solrizer', 'iss': 'solrizer', 'role': 'fedoraAdmin'},
    )


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


def get_client(config: Mapping[str, Any]) -> Client:
    try:
        endpoint = Endpoint(config['FCREPO_ENDPOINT'])
        auth = get_authenticator(config)
        session = get_session(config)

        if 'FCREPO_ORIGIN' in config:
            return ProxiedClient(
                endpoint=endpoint,
                origin_endpoint=Endpoint(config['FCREPO_ORIGIN']),
                auth=auth,
                session=session,
            )
        else:
            return Client(
                endpoint=endpoint,
                auth=auth,
                session=session,
            )
    except KeyError as e:
        logger.error(f'Configuration is missing a required key: {e}')
        raise ConfigurationError() from e


def get_repo(config: Mapping[str, Any], args: Mapping[str, Any]) -> Repository:
    plastron_cache_enabled = args.get('plastron-cache-enabled')
    if plastron_cache_enabled == 'no' or plastron_cache_enabled == '0':
        client = get_client({**config, 'PLASTRON_CACHE_ENABLED': False})
    elif plastron_cache_enabled == 'yes' or plastron_cache_enabled == '1':
        client = get_client({**config, 'PLASTRON_CACHE_ENABLED': True})
    else:
        client = get_client(config)

    return Repository(client=client)


def parse_indexers_param(indexers_param: str | None) -> list[str] | None:
    """Parse the `indexers` query parameter of comma-separated indexer
    names returning a list of indexer names.

    If `indexers_param` is None, returns None, indicating that configured
    indexers should be used instead.

    Args:
        indexers_param: The raw value of the `indexers` query parameter,
            or None if the parameter was not supplied.

    Returns:
        A list of validated indexer names, or None if no `indexers`
        parameter was provided.

    Raises:
        BadIndexersParameter: When any of the following occur:

            * The `indexers_param` parameter is an empty string
            * No valid indexer names are found after parsing
            * An identifier name is not a registered indexer
            * The list contains duplicate names
    """
    if indexers_param is None:
        # indexers parameter is optional, so just return None
        return None

    # Split on comma, filter out empty strings
    indexers = [indexer.strip() for indexer in indexers_param.split(',') if indexer.strip()]

    if not indexers:
        # No indexers provided, throw error
        raise BadIndexersParameter(f'No indexers found in "{indexers_param}"')

    # Check for invalid and duplicate indexers
    known_indexers = AVAILABLE_INDEXERS.names

    for indexer in indexers:
        if indexer not in known_indexers:
            raise BadIndexersParameter(value=f'"{indexer}" is not a recognized indexer.')

    if len(indexers) != len(set(indexers)):
        raise BadIndexersParameter(value=f'"{indexers_param}" has duplicate indexers.')

    return indexers


def create_app():
    start_time = datetime.now()
    app = Flask(__name__)
    app.config.from_prefixed_env('SOLRIZER')
    load_config_from_files(app.config)

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
        return render_template('index.html', version=__version__)

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

        indexers = parse_indexers_param(request.args.get('indexers', None))
        repo = get_repo(app.config, request.args)

        with Timer(
            name=f'create Solr document for {uri}',
            text='Time to {name}: {milliseconds:.3f} ms',
            logger=app.logger.info,
        ):
            try:
                resource: RepositoryResource = repo[uri].read()
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
                repo=repo,
                resource=resource,
                model_class=model_class,
                doc={'id': uri},
                config=app.config,
            )

            # Determine indexers using the model, unless already specified in
            # the request
            if not indexers:
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

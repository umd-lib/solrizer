import json
import logging
from pathlib import Path
from time import strftime
from typing import MutableMapping

import yaml
from flask import Flask, request
from plastron.client import Client, Endpoint
from plastron.models import ModelClassError, guess_model
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryError, RepositoryResource
from plastron.utils import envsubst
from requests_jwtauth import JWTSecretAuth
from werkzeug.exceptions import InternalServerError

from solrizer import __version__
from solrizer.errors import (
    NoResourceRequested,
    ProblemDetailError,
    ResourceNotAvailable,
    UnknownCommand,
    problem_detail_response,
)
from solrizer.indexers import IndexerContext, IndexerError

logging.basicConfig(level=logging.INFO)
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
    with the prefix "SOLRIZER_". In the file, use the name without the "SOLRIZER_"
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


def create_app():
    app = Flask(__name__)
    app.config.from_prefixed_env('SOLRIZER')
    load_config_from_files(app.config)

    client = Client(
        endpoint=Endpoint(app.config['FCREPO_ENDPOINT']),
        auth=JWTSecretAuth(
            secret=app.config['FCREPO_JWT_SECRET'], claims={'sub': 'solrizer', 'iss': 'solrizer', 'role': 'fedoraAdmin'}
        ),
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
              <label>URI: <input name="uri" type="text" size="80"/></label><button type="submit">Submit</button>
            </form>
            <hr/>
            <p id="version">{__version__}</p>
          </body>
        </html>
        '''

    @app.route('/health')
    def get_health():
        return {'status': 'ok'}

    @app.route('/doc')
    def get_doc():
        uri = request.args.get('uri')

        if uri is None:
            raise NoResourceRequested()

        command = request.args.get('command', None)
        if command not in ('add', 'update', None):
            raise UnknownCommand(value=command)

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
                # transform into an atomic update
                atomic_update = {}
                for k, v in doc.items():
                    if k in ('_root_', 'id'):
                        atomic_update[k] = v
                    else:
                        atomic_update[k] = {'set': v}
                doc = [atomic_update]
            case None:
                # just the plain document
                pass

        return json.dumps(doc, sort_keys=True), {'Content-Type': 'application/json;charset=utf-8'}

    # serve error responses using the RFC 9457 Problem Detail JSON format
    app.register_error_handler(ProblemDetailError, problem_detail_response)

    return app

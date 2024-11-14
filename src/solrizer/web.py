import json
import logging
from time import strftime

from flask import Flask, request
from plastron.client import Client, Endpoint
from plastron.models import ModelClassError, guess_model
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryError, RepositoryResource
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


def create_app():
    app = Flask(__name__)
    app.config.from_prefixed_env('SOLRIZER')

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

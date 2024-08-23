import os

from flask import Flask, request
from plastron.client import Client, Endpoint
from plastron.models import guess_model, ModelClassError
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryError, RepositoryResource
from requests_jwtauth import HTTPBearerAuth

from solrizer.errors import ResourceNotAvailable, NoResourceRequested, ProblemDetailError, problem_detail_response
from solrizer.indexers.content_model import get_model_fields

FCREPO_ENDPOINT = os.environ.get('FCREPO_ENDPOINT')
FCREPO_JWT_TOKEN = os.environ.get('FCREPO_JWT_TOKEN')


def create_app():
    app = Flask(__name__)

    client = Client(endpoint=Endpoint(FCREPO_ENDPOINT), auth=HTTPBearerAuth(FCREPO_JWT_TOKEN))
    app.config['repo'] = Repository(client=client)

    @app.route('/doc')
    def get_doc():
        uri = request.args.get('uri')

        if uri is None:
            raise NoResourceRequested()

        try:
            resource: RepositoryResource = app.config['repo'][uri].read()
        except RepositoryError as e:
            raise ResourceNotAvailable(uri=uri) from e

        doc = {'id': uri}

        # dynamically determine the model_class
        try:
            model_class = guess_model(resource.describe(RDFResource))
        except ModelClassError as e:
            app.logger.error(f'Unable to determine model class for {resource.url}')
            raise ResourceNotAvailable(uri=uri) from e

        obj = resource.describe(model_class)
        prefix = model_class.__name__.lower() + '__'
        doc.update(get_model_fields(obj, repo=app.config['repo'], prefix=prefix))

        return doc, {'Content-Type': 'application/json;charset=utf-8'}

    # serve error responses using the RFC 9457 Problem Detail JSON format
    app.register_error_handler(ProblemDetailError, problem_detail_response)

    return app

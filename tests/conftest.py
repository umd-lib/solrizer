from uuid import uuid4
from unittest.mock import MagicMock

import plastron.models.authorities
import plastron.validation.vocabularies
import pytest
from plastron.repo import RepositoryResource
from rdflib import Graph

import solrizer.web
from solrizer.indexers import SolrFields
from solrizer.web import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('SOLRIZER_FCREPO_ENDPOINT', 'http://localhost:8080/fcrepo/rest')
    monkeypatch.setenv('SOLRIZER_FCREPO_JWT_TOKEN', '')
    monkeypatch.setenv('SOLRIZER_FCREPO_JWT_SECRET', str(uuid4()))
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def proxies() -> SolrFields:
    return {
        'proxy__proxy_for__uri': 'url1',
        'proxy__next': [{
            'proxy__proxy_for__uri': 'url2',
            'proxy__next': [{
                'proxy__proxy_for__uri': 'url3',
            }]
        }]
    }


@pytest.fixture
def mock_vocabularies(monkeypatch, shared_datadir):
    def _get_vocabulary_graph(uri: str):
        basename = uri.split('#', 1)[0].rsplit('/', 1)[-1]
        graph = Graph()
        with (shared_datadir / f'{basename}.json').open() as fh:
            graph.parse(file=fh)
        return graph

    monkeypatch.setattr(plastron.validation.vocabularies, 'get_vocabulary_graph', _get_vocabulary_graph)

    return _get_vocabulary_graph


@pytest.fixture
def get_mock_resource():
    def _mock_resource(path, obj):
        mock_resource = MagicMock(spec=RepositoryResource, path=path)
        mock_resource.describe.return_value = obj
        return mock_resource
    return _mock_resource

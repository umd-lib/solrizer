from collections.abc import Mapping
from unittest.mock import MagicMock
from uuid import uuid4

import plastron.models.authorities
import plastron.validation.vocabularies
import pytest
from plastron.client import Endpoint
from plastron.models import ContentModeledResource
from plastron.rdfmapping.graph import TrackChangesGraph
from plastron.repo import RepositoryResource, Repository
from plastron.repo.pcdm import PCDMObjectResource, ProxyIterator
from rdflib import Graph, URIRef

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
def create_mock_repo():
    def _create_mock_repo(
        paths: Mapping[str, ContentModeledResource] = None,
        repo_url: str = 'http://example.com/fcrepo',
    ) -> Repository:
        def _lookup_path(key):
            if isinstance(key, slice):
                return str(key.start).replace(repo_url, '')
            else:
                return str(key).replace(repo_url, '')

        uri_mapping = {}
        mock_repo = MagicMock(spec=Repository)
        mock_repo.__getitem__ = lambda self, key: uri_mapping[URIRef(repo_url + _lookup_path(key))]
        mock_repo.endpoint = Endpoint(repo_url)
        for path, obj in (paths or {}).items():
            resource = MagicMock(spec=PCDMObjectResource)
            resource.repo = mock_repo
            resource.convert_to.return_value = resource
            resource.read.return_value = resource
            resource.describe.return_value = obj
            resource.path = path
            resource._graph = obj.graph
            resource.get_sequence.return_value = ProxyIterator(resource)
            uri_mapping[URIRef(repo_url + path)] = resource

        return mock_repo
    return _create_mock_repo


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
    def _mock_resource(path, obj, resource_class=RepositoryResource):
        mock_resource = MagicMock(spec=resource_class, path=path)
        mock_resource.describe.return_value = obj
        return mock_resource
    return _mock_resource

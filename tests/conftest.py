import pytest

from solrizer.indexers import SolrFields
from solrizer.web import create_app


@pytest.fixture
def app():
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

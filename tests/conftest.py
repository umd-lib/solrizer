import pytest

import solrizer.web


@pytest.fixture
def app():
    return solrizer.web.app


@pytest.fixture
def client(app):
    return app.test_client()

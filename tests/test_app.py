from pathlib import Path
from unittest.mock import MagicMock

import httpretty
from plastron.client import Endpoint, Client
from plastron.repo import Repository, RepositoryError, RepositoryResource


def test_doc_no_uri(client):
    response = client.get('/doc')
    assert response.status_code == 400
    assert response.content_type == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 400
    assert detail['title'] == 'No resource requested'
    assert detail['details'] == 'No resource URL or path was provided as part of this request.'


def test_doc_repository_error(app, client):
    mock_repo = MagicMock(spec=Repository)
    mock_resource = MagicMock(spec=RepositoryResource)
    mock_repo.__getitem__.return_value = mock_resource
    mock_resource.read.side_effect = RepositoryError()
    app.config['repo'] = mock_repo
    response = client.get('/doc?uri=http://example.com/fcrepo/foo')
    assert response.status_code == 404
    assert response.content_type == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 404
    assert detail['title'] == 'Resource is not available'
    assert detail['details'] == 'Resource at "http://example.com/fcrepo/foo" is not available from the repository.'


def register_uri_for_reading(uri: str, content_type: str, body: str):
    httpretty.register_uri(
        method=httpretty.HEAD,
        uri=uri,
        adding_headers={'Content-Type': content_type},
    )
    httpretty.register_uri(
        method=httpretty.GET,
        uri=uri,
        body=body,
        adding_headers={'Content-Type': content_type},
    )


@httpretty.activate()
def test_doc(client, datadir: Path):
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body=(datadir / 'item.nt').read_text(),
    )
    client.application.config['repo'] = Repository(client=Client(endpoint=Endpoint(url='http://example.com/fcrepo')))
    response = client.get('/doc?uri=http://example.com/fcrepo/foo')
    assert response.status_code == 200
    assert response.mimetype == 'application/json'
    result = response.json
    assert result['id'] == 'http://example.com/fcrepo/foo'


@httpretty.activate()
def test_doc_no_content_model(client):
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body='',
    )
    client.application.config['repo'] = Repository(client=Client(endpoint=Endpoint(url='http://example.com/fcrepo')))
    response = client.get('/doc?uri=http://example.com/fcrepo/foo')
    assert response.status_code == 404
    assert response.mimetype == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 404
    assert detail['title'] == 'Resource is not available'
    assert detail['details'] == 'Resource at "http://example.com/fcrepo/foo" is not available from the repository.'

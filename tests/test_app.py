import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpretty
import pytest
from plastron.client import Client, Endpoint
from plastron.repo import Repository, RepositoryError, RepositoryResource


@pytest.fixture
def repo():
    return Repository(client=Client(endpoint=Endpoint(url='http://example.com/fcrepo')))


def test_doc_no_uri(client):
    response = client.get('/doc')
    assert response.status_code == 400
    assert response.content_type == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 400
    assert detail['title'] == 'No resource requested'
    assert detail['details'] == 'No resource URL or path was provided as part of this request.'


@patch('solrizer.web.get_repo')
def test_doc_repository_error(mock_get_repo, app, client):
    mock_repo = MagicMock(spec=Repository)
    mock_resource = MagicMock(spec=RepositoryResource)
    mock_repo.__getitem__.return_value = mock_resource
    mock_resource.read.side_effect = RepositoryError()
    mock_get_repo.return_value = mock_repo
    response = client.get('/doc?uri=http://example.com/fcrepo/foo')
    assert response.status_code == 404
    assert response.content_type == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 404
    assert detail['title'] == 'Resource is not available'
    assert detail['details'] == 'Resource at "http://example.com/fcrepo/foo" is not available from the repository.'


@httpretty.activate()
@patch('solrizer.web.get_repo')
def test_doc_content_model_indexer_only(mock_get_repo, monkeypatch, client, datadir: Path, register_uri_for_reading):
    mock_get_repo.return_value = Repository(client=Client(endpoint=Endpoint(url='http://example.com/fcrepo')))
    monkeypatch.setitem(client.application.config, "INDEXERS", {'__default__': ['content_model']})
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body=(datadir / 'item.nt').read_text(),
    )
    response = client.get('/doc?uri=http://example.com/fcrepo/foo')
    assert response.status_code == 200
    assert response.mimetype == 'application/json'
    result = response.json
    assert result['id'] == 'http://example.com/fcrepo/foo'
    assert result['content_model_name__str'] == 'Item'


@httpretty.activate()
@patch('solrizer.web.get_repo')
def test_doc_no_content_model(mock_get_repo, client, repo, register_uri_for_reading):
    mock_get_repo.return_value = repo
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body='',
    )
    response = client.get('/doc?uri=http://example.com/fcrepo/foo')
    assert response.status_code == 404
    assert response.mimetype == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 404
    assert detail['title'] == 'Resource is not available'
    assert detail['details'] == 'Resource at "http://example.com/fcrepo/foo" is not available from the repository.'


@httpretty.activate()
@patch('solrizer.web.get_repo')
def test_doc_with_add_command(mock_get_repo, datadir, client, repo, register_uri_for_reading):
    mock_get_repo.return_value = repo
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body=(datadir / 'item.nt').read_text(),
    )
    response = client.get('/doc?uri=http://example.com/fcrepo/foo&command=add')
    assert response.status_code == 200
    assert response.mimetype == 'application/json'
    result = response.json
    assert 'add' in result
    assert 'doc' in result['add']
    doc = result['add']['doc']
    assert doc['id'] == 'http://example.com/fcrepo/foo'
    assert doc['content_model_name__str'] == 'Item'


@httpretty.activate()
@patch('solrizer.web.get_repo')
def test_doc_with_update_command(mock_get_repo, datadir, client, repo, register_uri_for_reading):
    mock_get_repo.return_value = repo
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body=(datadir / 'item.nt').read_text(),
    )
    register_uri_for_reading(
        uri='http://solr.example.com/fcrepo/select',
        content_type='application/json',
        body=json.dumps({
            'response': {
                'docs': [{
                    'id': 'http://example.com/fcrepo/foo',
                    'object__title__txt_de': 'der Hund',
                    'object__title__txt': 'Moonpig',
                }],
            },
        }),
    )
    client.application.config['SOLR_QUERY_ENDPOINT'] = 'http://solr.example.com/fcrepo/select'
    response = client.get('/doc?uri=http://example.com/fcrepo/foo&command=update')
    assert response.status_code == 200
    assert response.mimetype == 'application/json'
    result = response.json
    assert isinstance(result, list)
    doc = result[0]
    assert doc['id'] == 'http://example.com/fcrepo/foo'
    assert doc['content_model_name__str'] == {'set': 'Item'}


@httpretty.activate()
def test_doc_with_update_command_no_solr_endpoint(datadir, client, repo, register_uri_for_reading):
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body=(datadir / 'item.nt').read_text(),
    )
    register_uri_for_reading(
        uri='http://solr.example.com/fcrepo/select',
        content_type='application/json',
        body=json.dumps({
            'response': {
                'docs': [{
                    'id': 'http://example.com/fcrepo/foo',
                    'object__title__txt_de': 'der Hund',
                    'object__title__txt': 'Moonpig',
                }],
            },
        }),
    )
    client.application.config['repo'] = repo
    response = client.get('/doc?uri=http://example.com/fcrepo/foo&command=update')
    assert response.status_code == 500
    assert response.mimetype == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 500
    assert detail['title'] == 'Configuration error'
    assert detail['details'] == 'The server is incorrectly configured.'


@httpretty.activate()
def test_doc_with_unknown_command(datadir, client, repo, register_uri_for_reading):
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body=(datadir / 'item.nt').read_text(),
    )
    client.application.config['repo'] = repo
    response = client.get('/doc?uri=http://example.com/fcrepo/foo&command=NOT_A_VALID_COMMAND')
    assert response.status_code == 400
    assert response.mimetype == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 400
    assert detail['title'] == 'Unknown command'
    assert detail['details'] == '"NOT_A_VALID_COMMAND" is not a recognized value for the "command" parameter.'

from contextlib import nullcontext
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock

import httpretty
import pytest
from plastron.client import Client, Endpoint
from plastron.repo import Repository, RepositoryError, RepositoryResource

from solrizer.errors import BadIndexersParameter
from solrizer.web import parse_indexers_param


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


@httpretty.activate()
def test_doc_content_model_indexer_only(monkeypatch, client, datadir: Path, register_uri_for_reading):
    monkeypatch.setitem(client.application.config, "INDEXERS", {'__default__': ['content_model']})
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
    assert result['content_model_name__str'] == 'Item'


@httpretty.activate()
def test_doc_no_content_model(client, repo, register_uri_for_reading):
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body='',
    )
    client.application.config['repo'] = repo
    response = client.get('/doc?uri=http://example.com/fcrepo/foo')
    assert response.status_code == 404
    assert response.mimetype == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 404
    assert detail['title'] == 'Resource is not available'
    assert detail['details'] == 'Resource at "http://example.com/fcrepo/foo" is not available from the repository.'


@httpretty.activate()
def test_doc_with_add_command(datadir, client, repo, register_uri_for_reading):
    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body=(datadir / 'item.nt').read_text(),
    )
    client.application.config['repo'] = repo
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
def test_doc_with_update_command(datadir, client, repo, register_uri_for_reading):
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


@pytest.mark.parametrize(
    ('identifiers_param', 'expected'),
    [
        (None, nullcontext(None)),
        ('', pytest.raises(BadIndexersParameter)),
        ('NOT_A_VALID_INDEXER', pytest.raises(BadIndexersParameter)),
        ('content_model,NOT_A_VALID_INDEXER', pytest.raises(BadIndexersParameter)),
        ('content_model,dates,content_model', pytest.raises(BadIndexersParameter)),
        ('content_model', nullcontext(['content_model'])),
        ('content_model,dates', nullcontext(['content_model', 'dates'])),
        ('content_model, ,dates,,handles,', nullcontext(['content_model', 'dates', 'handles'])),
    ]
)
def test_parse_indexers_param(identifiers_param, expected):
    with expected as e:
        assert parse_indexers_param(identifiers_param) == e


@httpretty.activate()
def test_doc_with_empty_indexers_param(client):
    response = client.get('/doc?uri=http://example.com/fcrepo/foo&indexers=')

    assert response.status_code == 400
    assert response.mimetype == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 400
    assert detail['title'] == 'Bad indexers parameter'
    assert detail['details'] == 'No indexers found in ""'


@httpretty.activate()
def test_doc_with_unknown_indexer(client):
    response = client.get('/doc?uri=http://example.com/fcrepo/foo&indexers=NOT_A_VALID_INDEXER')

    assert response.status_code == 400
    assert response.mimetype == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 400
    assert detail['title'] == 'Bad indexers parameter'
    assert detail['details'] == '"NOT_A_VALID_INDEXER" is not a recognized indexer.'


@httpretty.activate()
def test_doc_with_duplicate_indexers(client):
    response = client.get('/doc?uri=http://example.com/fcrepo/foo&indexers=content_model,dates,content_model')

    assert response.status_code == 400
    assert response.mimetype == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 400
    assert detail['title'] == 'Bad indexers parameter'
    assert detail['details'] == '"content_model,dates,content_model" has duplicate indexers.'


@httpretty.activate()
def test_doc_with_single_indexer(datadir, client, repo, register_uri_for_reading, caplog):
    caplog.set_level(logging.INFO)

    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body=(datadir / 'item.nt').read_text(),
    )
    client.application.config['repo'] = repo

    response = client.get('/doc?uri=http://example.com/fcrepo/foo&indexers=content_model')

    assert "Running indexers: [\'content_model\']" in caplog.text
    assert response.status_code == 200
    assert response.mimetype == 'application/json'
    result = response.json

    assert result['id'] == 'http://example.com/fcrepo/foo'
    assert result['content_model_name__str'] == 'Item'


@httpretty.activate()
def test_doc_with_multiple_indexers(datadir, client, repo, register_uri_for_reading, caplog):
    caplog.set_level(logging.INFO)

    register_uri_for_reading(
        uri='http://example.com/fcrepo/foo',
        content_type='application/n-triples',
        body=(datadir / 'item.nt').read_text(),
    )
    client.application.config['repo'] = repo

    response = client.get('/doc?uri=http://example.com/fcrepo/foo&indexers=content_model,facets')

    assert "Running indexers: [\'content_model\', \'facets\']" in caplog.text
    assert response.status_code == 200
    assert response.mimetype == 'application/json'
    result = response.json
    assert result['id'] == 'http://example.com/fcrepo/foo'
    assert result['content_model_name__str'] == 'Item'
    assert "Visible" in result['visibility__facet']

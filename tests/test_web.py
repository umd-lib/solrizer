from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from requests import Session
from requests_cache import BaseCache, CachedSession

from solrizer.web import get_session, load_config_from_files


def test_load_config_from_files(datadir):
    config = {
        'INDEXERS_FILE': datadir / 'indexers.yml'
    }
    load_config_from_files(config)
    assert 'INDEXERS' in config
    assert config == {
        'INDEXERS_FILE': datadir / 'indexers.yml',
        'INDEXERS': {'Item': ['content_model']},
    }


def test_load_config_from_files_unknown_extension(datadir):
    config = {
        'INDEXERS_FILE': datadir / 'indexers.bad_extension'
    }
    with pytest.raises(RuntimeError):
        load_config_from_files(config)


def test_load_config_from_files_file_not_found(datadir):
    config = {
        'INDEXERS_FILE': datadir / 'no_file.yml'
    }
    with pytest.raises(RuntimeError):
        load_config_from_files(config)


@pytest.mark.parametrize(
    ('config', 'expected_class'),
    [
        ({}, Session),
        ({'PLASTRON_CACHE_ENABLED': False}, Session),
        ({'PLASTRON_CACHE_ENABLED': True}, CachedSession),
    ],
)
@patch('solrizer.web.init_backend')
def test_get_session_class(mock_init_backend, config: dict[str, Any], expected_class):
    mock_init_backend.return_value = BaseCache()
    session = get_session(config)
    assert isinstance(session, expected_class)


@patch('solrizer.web.init_backend')
def test_get_session_cache_backend_params(mock_init_backend: MagicMock):
    mock_init_backend.return_value = BaseCache()
    get_session({
        'PLASTRON_CACHE_ENABLED': True,
        'PLASTRON_CACHE_NAME': 'test_cache',
        'PLASTRON_CACHE_BACKEND': 'experimental',
        'PLASTRON_CACHE_PARAMS': {'host': 'example.com', 'port': 1234},
    })
    mock_init_backend.assert_called_with(
        cache_name='test_cache',
        backend='experimental',
        host='example.com',
        port=1234,
    )


def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.mimetype == 'text/html'
    assert '<h1>Solrizer</h1>' in response.text


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.is_json
    health = response.json
    assert 'status' in health
    assert 'uptime' in health
    assert 'memory' in health
    memory = health['memory']
    assert 'available' in memory
    assert 'total' in memory
    assert 'used' in memory
    assert 'used_percent' in memory


def test_session_before_request(client, app):
    response = client.get('/', query_string={'plastron-cache-enabled': 'no'})
    assert response.status_code == 200
    assert isinstance(app.config['repo'].client.session, Session)

    response = client.get('/', query_string={'plastron-cache-enabled': '0'})
    assert response.status_code == 200
    assert isinstance(app.config['repo'].client.session, Session)

    response = client.get('/', query_string={'plastron-cache-enabled': 'yes'})
    assert response.status_code == 200
    assert isinstance(app.config['repo'].client.session, CachedSession)

    response = client.get('/', query_string={'plastron-cache-enabled': '1'})
    assert response.status_code == 200
    assert isinstance(app.config['repo'].client.session, CachedSession)

    response = client.get('/')
    assert response.status_code == 200
    assert isinstance(app.config['repo'].client.session, CachedSession)

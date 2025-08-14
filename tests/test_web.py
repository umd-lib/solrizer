import pytest

from solrizer.web import load_config_from_files


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

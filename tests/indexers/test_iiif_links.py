from unittest.mock import MagicMock

import pytest
from plastron.client import Client, Endpoint
from plastron.models.umd import Item
from plastron.repo import Repository, RepositoryResource

from solrizer.indexers import IndexerContext
from solrizer.indexers.iiif_links import iiif_identifier, iiif_links_fields


@pytest.mark.parametrize(
    ('path', 'prefix', 'expected_identifier'),
    [
        ('/foo/bar', 'fcrepo:', 'fcrepo:foo:bar'),
        ('/foo', 'fcrepo:', 'fcrepo:foo'),
        ('/foo', '', 'foo'),
    ]
)
def test_iiif_identifier(path, prefix, expected_identifier):
    assert iiif_identifier(path, prefix) == expected_identifier


def test_iiif_links_fields(monkeypatch, proxies):
    members = [
        {'id': 'url1', 'pcdmobject__title__txt': 'Bar 1', 'pcdmobject__has_file': [
            {'id': 'http://example.com/fcrepo/foo/obj1/fileX'},
        ]},
        {'id': 'url2', 'pcdmobject__title__txt': 'Bar 2', 'pcdmobject__has_file': [
            {'id': 'http://example.com/fcrepo/foo/obj2/fileX'},
        ]},
        {'id': 'url3', 'pcdmobject__title__txt': 'Bar 3', 'pcdmobject__has_file': [
            {'id': 'http://example.com/fcrepo/foo/obj3/fileX'},
        ]},
    ]
    ctx = IndexerContext(
        repo=Repository(client=Client(endpoint=Endpoint('http://example.com/fcrepo'))),
        resource=MagicMock(spec=RepositoryResource, path='/foo'),
        model_class=Item,
        doc={
            'id': 'http://example.com/fcrepo/foo',
            'item__has_member': members,
            'item__first': [proxies]
        },
        config={
            'IIIF_IDENTIFIER_PREFIX': 'fcrepo:',
            'IIIF_THUMBNAIL_URL_PATTERN': 'http://iiif.example.com/thumbnail/{+id}',
            'IIIF_MANIFESTS_URL_PATTERN': 'http://iiif.example.com/manifest/{+id}',
        },
    )
    fields = iiif_links_fields(ctx)
    assert fields == {
        'iiif_manifest__id': 'fcrepo:foo',
        'iiif_manifest__uri': 'http://iiif.example.com/manifest/fcrepo:foo',
        'iiif_thumbnail_identifier__sequence': [
            'fcrepo:foo:obj1:fileX',
            'fcrepo:foo:obj2:fileX',
            'fcrepo:foo:obj3:fileX',
        ],
        'iiif_thumbnail_uri__sequence': [
            'http://iiif.example.com/thumbnail/fcrepo:foo:obj1:fileX',
            'http://iiif.example.com/thumbnail/fcrepo:foo:obj2:fileX',
            'http://iiif.example.com/thumbnail/fcrepo:foo:obj3:fileX',
        ]
    }

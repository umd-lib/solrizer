import pytest
from plastron.models.ldp import LDPContainer
from plastron.models.ore import Proxy
from plastron.models.umd import Item
from plastron.repo.pcdm import ProxyIterator
from rdflib import URIRef

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


def test_iiif_links_fields(monkeypatch, proxies, create_mock_repo):
    members = [
        {'id': '/url1', 'page__title__txt': 'Bar 1', 'page__has_file': [
            {'id': 'http://example.com/fcrepo/foo/obj1/fileX'},
        ]},
        {'id': '/url2', 'page__title__txt': 'Bar 2', 'page__has_file': [
            {'id': 'http://example.com/fcrepo/foo/obj2/fileX'},
        ]},
        {'id': '/url3', 'page__title__txt': 'Bar 3', 'page__has_file': [
            {'id': 'http://example.com/fcrepo/foo/obj3/fileX'},
        ]},
    ]
    mock_repo = create_mock_repo({
        '/proxy1': Proxy(proxy_for=URIRef('/url1'), next=URIRef('/proxy2')),
        '/proxy2': Proxy(proxy_for=URIRef('/url2'), next=URIRef('/proxy3')),
        '/proxy3': Proxy(proxy_for=URIRef('/url3')),
        '/foo': Item(first=URIRef('/proxy1')),
        '/foo/f': LDPContainer(),
        '/foo/m': LDPContainer(),
    })
    ctx = IndexerContext(
        repo=mock_repo,
        resource=mock_repo['/foo'],
        model_class=Item,
        doc={
            'id': 'http://example.com/fcrepo/foo',
            'object__has_member': members,
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
        'iiif_thumbnail_sequence__ids': [
            'fcrepo:foo:obj1:fileX',
            'fcrepo:foo:obj2:fileX',
            'fcrepo:foo:obj3:fileX',
        ],
        'iiif_thumbnail_sequence__uris': [
            'http://iiif.example.com/thumbnail/fcrepo:foo:obj1:fileX',
            'http://iiif.example.com/thumbnail/fcrepo:foo:obj2:fileX',
            'http://iiif.example.com/thumbnail/fcrepo:foo:obj3:fileX',
        ]
    }

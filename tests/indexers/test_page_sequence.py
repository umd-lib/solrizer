import pytest
from plastron.models.ldp import LDPContainer
from plastron.models.ore import Proxy
from plastron.models.umd import Item
from plastron.rdfmapping.resources import is_iterable
from rdflib import URIRef

from solrizer.indexers import IndexerContext, SolrFields
from solrizer.indexers.page_sequence import get_members_by_uri, PageSequence, page_sequence_fields


@pytest.fixture
def doc(proxies) -> SolrFields:
    return {
        'id': 'foo',
        'object__has_member': [
            {'id': '/url1', 'page__title__txt': 'Bar 1'},
            {'id': '/url2', 'page__title__txt': 'Bar 2'},
            {'id': '/url3', 'page__title__txt': 'Bar 3'},
        ],
    }


@pytest.fixture
def context(doc, create_mock_repo):
    mock_repo = create_mock_repo({
        '/proxy1': Proxy(proxy_for=URIRef('/url1'), next=URIRef('/proxy2')),
        '/proxy2': Proxy(proxy_for=URIRef('/url2'), next=URIRef('/proxy3')),
        '/proxy3': Proxy(proxy_for=URIRef('/url3')),
        '/item': Item(first=URIRef('/proxy1')),
        '/item/m': LDPContainer(),
        '/item/f': LDPContainer(),
    })
    return IndexerContext(
        repo=mock_repo,
        resource=mock_repo[URIRef('/item')],
        model_class=Item,
        doc=doc,
        config={},
    )


def test_get_members_by_id(context):
    members = get_members_by_uri(context)
    assert members['/url1'] == {'id': '/url1', 'page__title__txt': 'Bar 1'}
    assert members['/url2'] == {'id': '/url2', 'page__title__txt': 'Bar 2'}
    assert members['/url3'] == {'id': '/url3', 'page__title__txt': 'Bar 3'}


def test_page_sequence(context):
    sequence = PageSequence(context)
    assert sequence.uris == ['/url1', '/url2', '/url3']
    assert sequence.labels == ['Bar 1', 'Bar 2', 'Bar 3']
    assert sequence.pages == [
        {'id': '/url1', 'page__title__txt': 'Bar 1'},
        {'id': '/url2', 'page__title__txt': 'Bar 2'},
        {'id': '/url3', 'page__title__txt': 'Bar 3'},
    ]
    assert is_iterable(sequence)
    assert sequence[0] == {'id': '/url1', 'page__title__txt': 'Bar 1'}


def test_empty_page_sequence_fields(create_mock_repo):
    mock_repo = create_mock_repo({'item': Item()})
    context = IndexerContext(
        repo=mock_repo,
        resource=mock_repo[URIRef('item')],
        model_class=Item,
        doc={},
        config={},
    )
    fields = page_sequence_fields(context)
    assert fields == {}


def test_page_sequence_fields(context):
    fields = page_sequence_fields(context)
    assert fields == {
        'page_uri_sequence__uris': ['/url1', '/url2', '/url3'],
        'page_label_sequence__txts': ['Bar 1', 'Bar 2', 'Bar 3'],
    }

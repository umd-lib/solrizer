from unittest.mock import MagicMock

import pytest
from plastron.models.umd import Item
from plastron.rdfmapping.resources import is_iterable
from plastron.repo import Repository, RepositoryResource

from solrizer.indexers import IndexerContext, SolrFields
from solrizer.indexers.page_sequence import get_members_by_uri, follow_sequence, PageSequence, page_sequence_fields


@pytest.fixture
def doc(proxies) -> SolrFields:
    return {
        'id': 'foo',
        'item__has_member': [
            {'id': 'url1', 'page__title__txt': 'Bar 1'},
            {'id': 'url2', 'page__title__txt': 'Bar 2'},
            {'id': 'url3', 'page__title__txt': 'Bar 3'},
        ],
        'item__first': [proxies],
    }


@pytest.fixture
def context(doc):
    return IndexerContext(
        repo=MagicMock(spec=Repository),
        resource=MagicMock(spec=RepositoryResource),
        model_class=Item,
        doc=doc,
        config={},
    )


def test_get_members_by_id(context):
    members = get_members_by_uri(context)
    assert members['url1'] == {'id': 'url1', 'page__title__txt': 'Bar 1'}
    assert members['url2'] == {'id': 'url2', 'page__title__txt': 'Bar 2'}
    assert members['url3'] == {'id': 'url3', 'page__title__txt': 'Bar 3'}


def test_follow_sequence(proxies):
    assert list(follow_sequence(proxies)) == ['url1', 'url2', 'url3']


def test_page_sequence(context):
    sequence = PageSequence(context)
    assert sequence.uris == ['url1', 'url2', 'url3']
    assert sequence.labels == ['Bar 1', 'Bar 2', 'Bar 3']
    assert sequence.pages == [
        {'id': 'url1', 'page__title__txt': 'Bar 1'},
        {'id': 'url2', 'page__title__txt': 'Bar 2'},
        {'id': 'url3', 'page__title__txt': 'Bar 3'},
    ]
    assert is_iterable(sequence)
    assert sequence[0] == {'id': 'url1', 'page__title__txt': 'Bar 1'}


def test_empty_page_sequence_fields():
    context = IndexerContext(
        repo=MagicMock(spec=Repository),
        resource=MagicMock(spec=RepositoryResource),
        model_class=Item,
        doc={},
        config={},
    )
    fields = page_sequence_fields(context)
    assert fields == {}


def test_page_sequence_fields(context):
    fields = page_sequence_fields(context)
    assert fields == {
        'page_uri_sequence__uris': ['url1', 'url2', 'url3'],
        'page_label_sequence__txts': ['Bar 1', 'Bar 2', 'Bar 3'],
    }

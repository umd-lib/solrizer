from unittest.mock import MagicMock

import pytest
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryResource

from solrizer.indexers import IndexerContext, IndexerError
from solrizer.indexers.aggregate_fields import aggregate_fields


@pytest.fixture
def context_with_settings():
    def _context(settings):
        return IndexerContext(
            repo=MagicMock(Repository),
            resource=MagicMock(spec=RepositoryResource),
            model_class=RDFResource,
            doc={
                'title__txt': 'foo',
                'description__txt': 'bar',
                'identifier__id': '0123',
                'creator': [
                    {'agent__label__txt': 'John Doe'}
                ],
                'publisher': [
                    {'agent__label__txt': 'Eric Gen'}
                ],
            },
            config={
                'INDEXER_SETTINGS': {
                    'aggregate_fields': settings
                }
            },
            settings=settings,
        )

    return _context


def test_aggregate_fields(context_with_settings):
    fields = aggregate_fields(
        context_with_settings({
            'text': [
                '.title__txt',
                '.description__txt',
                '..|objects|.agent__label__txt',
            ]
        })
    )
    assert set(fields['text']) == {'foo', 'bar', 'John Doe', 'Eric Gen'}


def test_aggregate_fields_invalid_jq(context_with_settings):
    with pytest.raises(IndexerError):
        aggregate_fields(
            context_with_settings({'text': ['~~ invalid jq query !!']})
        )

from unittest.mock import MagicMock

import pytest
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryResource

import solrizer.indexers
from solrizer.indexers import IndexerError, IndexerContext


@pytest.fixture
def ctx():
    return IndexerContext(
        repo=MagicMock(spec=Repository),
        resource=MagicMock(spec=RepositoryResource),
        model_class=RDFResource,
        doc={},
    )


def test_invalid_indexer(ctx):
    with pytest.raises(IndexerError) as e:
        ctx.run(['DOES_NOT_EXIST'])
    assert str(e.value) == "No indexer named 'DOES_NOT_EXIST' is registered"


def test_indexer_error(ctx, monkeypatch):
    mock_indexer = MagicMock()
    mock_indexer.load.return_value = mock_indexer
    mock_indexer.side_effect = IndexerError('failed')
    monkeypatch.setattr(solrizer.indexers, 'AVAILABLE_INDEXERS', {'foo': mock_indexer})
    with pytest.raises(IndexerError) as e:
        ctx.run(['foo'])
    assert str(e.value) == 'failed'

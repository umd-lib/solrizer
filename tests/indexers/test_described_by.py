from unittest.mock import MagicMock

import pytest
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import RepositoryResource, Repository

from solrizer.indexers import IndexerContext
from solrizer.indexers.described_by import described_by_field


@pytest.mark.parametrize(
    ('url', 'description_url', 'expected_value'),
    [
        (
            'http://example.com/fcrepo/rest/123',
            'http://example.com/fcrepo/rest/123/fcr:metadata',
            'http://example.com/fcrepo/rest/123/fcr:metadata',
        ),
        # when the `description_url` is None (i.e., this is an RDF source),
        # should fall back to using the plain `url` for the `described_by__uri` field
        (
            'http://example.com/fcrepo/rest/123',
            None,
            'http://example.com/fcrepo/rest/123',
        ),
    ]
)
def test_described_by(url, description_url, expected_value):
    mock_resource = MagicMock(spec=RepositoryResource)
    mock_resource.url = url
    mock_resource.description_url = description_url
    context = IndexerContext(
        repo=MagicMock(spec=Repository),
        resource=mock_resource,
        model_class=RDFResource,
        doc={'id': 'foo'},
        config={},
    )
    fields = described_by_field(context)
    assert fields['described_by__uri'] == expected_value

from unittest.mock import MagicMock

import pytest
from plastron.namespaces import umdaccess, umd
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryResource

from solrizer.indexers import IndexerContext
from solrizer.indexers.discoverability import discoverability_fields


@pytest.mark.parametrize(
    ('obj', 'expected_fields'),
    [
        (
            RDFResource(),
            {'is_published': False, 'is_hidden': False, 'is_top_level': False, 'is_discoverable': False},
        ),
        (
            RDFResource(rdf_type=[umd.Item]),
            {'is_published': False, 'is_hidden': False, 'is_top_level': True, 'is_discoverable': False},
        ),
        (
            RDFResource(rdf_type=[umdaccess.Published, umd.Item]),
            {'is_published': True, 'is_hidden': False, 'is_top_level': True, 'is_discoverable': True},
        ),
        (
            RDFResource(rdf_type=[umdaccess.Published, umdaccess.Hidden, umd.Item]),
            {'is_published': True, 'is_hidden': True, 'is_top_level': True, 'is_discoverable': False},
        ),
        (
            RDFResource(rdf_type=[umdaccess.Published, umdaccess.Hidden]),
            {'is_published': True, 'is_hidden': True, 'is_top_level': False, 'is_discoverable': False},
        ),
        (
            RDFResource(rdf_type=[umdaccess.Published]),
            {'is_published': True, 'is_hidden': False, 'is_top_level': False, 'is_discoverable': False},
        ),
    ]
)
def test_discoverability(monkeypatch, obj, expected_fields):
    context = IndexerContext(
        repo=MagicMock(spec=Repository),
        resource=MagicMock(spec=RepositoryResource),
        model_class=RDFResource,
        doc={'id': 'foo'},
        config={},
    )
    monkeypatch.setattr(context, 'obj', obj)
    fields = discoverability_fields(context)
    assert fields == expected_fields

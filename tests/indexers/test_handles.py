from unittest.mock import MagicMock

import pytest
from plastron.handles import HandleBearingResource
from plastron.models import ContentModeledResource
from plastron.namespaces import umdtype
from plastron.repo import Repository, RepositoryResource
from rdflib import Literal

from solrizer.indexers import IndexerContext
from solrizer.indexers.handles import find_handle_property, handle_fields


class ObjectWithoutHandle(ContentModeledResource):
    pass


class ObjectWithHandle(ContentModeledResource, HandleBearingResource):
    pass


def test_find_handle_property():
    prop = find_handle_property(ObjectWithHandle())
    assert prop is not None


def test_find_handle_property_no_handle():
    prop = find_handle_property(ObjectWithoutHandle())
    assert prop is None


@pytest.fixture
def context_with_settings(monkeypatch):
    def _context(settings):
        context = IndexerContext(
            repo=MagicMock(Repository),
            resource=MagicMock(spec=RepositoryResource),
            model_class=ObjectWithHandle,
            doc={},
            config={
                'INDEXER_SETTINGS': {
                    'handles': settings
                }
            },
            settings=settings,
        )
        obj = ObjectWithHandle(
            handle=Literal('hdl:1903.1/123', datatype=umdtype.handle),
        )
        monkeypatch.setattr(context, 'obj', obj)
        return context

    return _context


def test_handle_fields(context_with_settings):
    ctx = context_with_settings({'proxy_prefix': 'http://example.net/hdl/'})
    fields = handle_fields(ctx)
    assert fields['handle__id'] == '1903.1/123'
    assert fields['handle__uri'] == 'info:hdl/1903.1/123'
    assert fields['handle_proxied__uri'] == 'http://example.net/hdl/1903.1/123'

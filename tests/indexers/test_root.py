from unittest.mock import MagicMock

import pytest
from plastron.models import ContentModeledResource
from plastron.namespaces import dcterms, pcdm
from plastron.rdfmapping.descriptors import DataProperty, ObjectProperty
from plastron.repo import Repository, RepositoryResource
from rdflib import URIRef

import solrizer.indexers.root
from solrizer.indexers import IndexerContext, IndexerError
from solrizer.indexers.root import root_field


class TopLevelModelClass(ContentModeledResource):
    is_top_level = True

    title = DataProperty(dcterms.title)


class PageLevelModelClass(ContentModeledResource):
    is_top_level = False

    member_of = ObjectProperty(pcdm.memberOf, cls=TopLevelModelClass)


class FileLevelModelClass(ContentModeledResource):
    is_top_level = False

    file_of = ObjectProperty(pcdm.fileOf, cls=PageLevelModelClass)


# is marked as not top-level, but lacks any properties that could be
# used to navigate to a parent resource (member_of or file_of)
class OrphanModelClass(ContentModeledResource):
    is_top_level = False


def test_root_field_for_top_level():
    context = IndexerContext(
        repo=MagicMock(spec=Repository),
        resource=MagicMock(spec=RepositoryResource),
        model_class=TopLevelModelClass,
        doc={},
        config={},
    )

    assert root_field(context) == {}


def test_root_field_for_page_level(monkeypatch):
    monkeypatch.setattr(solrizer.indexers.root, 'guess_model', lambda _: TopLevelModelClass)
    page_obj = PageLevelModelClass(uri='http://example.com/fcrepo/foo/p1', member_of=URIRef('http://example.com/fcrepo/foo'))
    parent_obj = TopLevelModelClass(uri='http://example.com/fcrepo/foo')

    repo = MagicMock(spec=Repository)

    page_resource = MagicMock(spec=RepositoryResource)
    page_resource.describe.return_value = page_obj

    parent_resource = MagicMock(spec=RepositoryResource)
    parent_resource.read.return_value = parent_resource
    parent_resource.describe.return_value = parent_obj
    repo.get_resource.return_value = parent_resource

    context = IndexerContext(
        repo=repo,
        resource=page_resource,
        model_class=PageLevelModelClass,
        doc={},
        config={},
    )

    fields = root_field(context)
    assert fields['_root_'] == 'http://example.com/fcrepo/foo'


def test_root_field_for_file_level(monkeypatch):
    def _guess_model(obj):
        if isinstance(obj, FileLevelModelClass):
            return FileLevelModelClass
        elif isinstance(obj, PageLevelModelClass):
            return PageLevelModelClass
        else:
            return TopLevelModelClass

    monkeypatch.setattr(solrizer.indexers.root, 'guess_model', _guess_model)

    file_obj = FileLevelModelClass(uri='http://example.com/fcrepo/foo/p1/file', file_of=URIRef('http://example.com/fcrepo/foo/p1'))
    page_obj = PageLevelModelClass(uri='http://example.com/fcrepo/foo/p1', member_of=URIRef('http://example.com/fcrepo/foo'))
    root_obj = TopLevelModelClass(uri='http://example.com/fcrepo/foo')

    repo = MagicMock(spec=Repository)

    file_resource = MagicMock(spec=RepositoryResource)
    file_resource.read.return_value = file_resource
    file_resource.describe.return_value = file_obj

    page_resource = MagicMock(spec=RepositoryResource)
    page_resource.read.return_value = page_resource
    page_resource.describe.return_value = page_obj

    root_resource = MagicMock(spec=RepositoryResource)
    root_resource.read.return_value = root_resource
    root_resource.describe.return_value = root_obj

    repo.get_resource.side_effect = [page_resource, root_resource]

    context = IndexerContext(
        repo=repo,
        resource=file_resource,
        model_class=FileLevelModelClass,
        doc={},
        config={},
    )

    fields = root_field(context)
    assert fields['_root_'] == 'http://example.com/fcrepo/foo'


def test_root_field_error(monkeypatch):
    monkeypatch.setattr(solrizer.indexers.root, 'guess_model', lambda _: OrphanModelClass)

    orphan_obj = OrphanModelClass()
    orphan_resource = MagicMock(spec=RepositoryResource)
    orphan_resource.read.return_value = orphan_resource
    orphan_resource.describe.return_value = orphan_obj

    context = IndexerContext(
        repo=MagicMock(spec=Repository),
        resource=orphan_resource,
        model_class=OrphanModelClass,
        doc={},
        config={},
    )
    with pytest.raises(IndexerError):
        root_field(context)

"""
Indexer Name: **`root`**

Indexer implementation function: `root_field()`

Prerequisites: None

Output fields:

| Field    | Python Type | Solr Type |
|----------|-------------|-----------|
| `_root_` | `str`       | string    |
"""

from typing import Optional

from plastron.models import ContentModeledResource, guess_model
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import RepositoryResource
from rdflib import URIRef

from solrizer.indexers import IndexerContext, SolrFields, IndexerError


def find_top_level_resource_uri(ctx: IndexerContext, obj: ContentModeledResource) -> Optional[URIRef]:
    """Given a resource, attempt to determine the top-level object to which it
    ultimately belongs by following the `member_of` and/or `file_of` properties.
    Raises an `IndexerError` if the resource has neither of those properties."""

    if hasattr(obj, 'member_of'):
        parent_uri = obj.member_of.value
    elif hasattr(obj, 'file_of'):
        parent_uri = obj.file_of.value
    else:
        raise IndexerError(f'Unable to determine top-level parent of {obj.uri}')

    parent_resource: RepositoryResource = ctx.repo.get_resource(parent_uri).read()
    parent_model = guess_model(parent_resource.describe(RDFResource))
    if parent_model.is_top_level:
        return parent_uri
    else:
        return find_top_level_resource_uri(ctx, parent_resource.describe(parent_model))


def root_field(ctx: IndexerContext) -> SolrFields:
    """Indexer function that adds a `_root_` field (used by Solr to manage
    nested documents) for any non-top-level resources being indexed. If the
    resource is a top-level resource, this indexer does not add the field."""

    if ctx.model_class.is_top_level:
        return {}

    obj = ctx.resource.describe(ctx.model_class)
    uri = find_top_level_resource_uri(ctx, obj)
    return {'_root_': str(uri)}

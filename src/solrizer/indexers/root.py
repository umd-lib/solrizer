from typing import Optional

from plastron.models import ContentModeledResource, guess_model
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import RepositoryResource
from rdflib import URIRef

from solrizer.indexers import IndexerContext, SolrFields, IndexerError


def find_top_level_resource_uri(ctx: IndexerContext, obj: ContentModeledResource) -> Optional[URIRef]:
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
    if ctx.model_class.is_top_level:
        return {}

    obj = ctx.resource.describe(ctx.model_class)
    uri = find_top_level_resource_uri(ctx, obj)
    return {'_root_': str(uri)}

"""
Indexer Name: **`handles`**

Indexer implementation function: `handle_fields()`

Prerequisites: Must run **after** the [`content_model`](./content_model) indexer

Output fields:

| Field                | Python Type | Solr Type |
|----------------------|-------------|-----------|
| `handle__id`         | `str`       | string    |
| `handle__uri`        | `str`       | string    |
| `handle_proxied_uri` | `str`       | string    |
"""

from plastron.models import ContentModeledResource
from plastron.namespaces import umdtype
from plastron.rdfmapping.properties import RDFDataProperty

from solrizer.indexers import IndexerContext, SolrFields
from solrizer.handles import Handle, HandleValueError

HANDLE_PROXY_BASE_URL = 'http://hdl.handle.net/'

POSSIBLE_HANDLE_FIELDS = [
    'archival_collection__same_as__uris',
]

def handle_fields(ctx: IndexerContext) -> SolrFields:
    """Indexer function that adds fields for handles in various formats. Uses
    `find_handle_property()` to get the first property of the context object
    that has a `umdtype:handle` datatype."""
    fields = {}
    if prop := find_handle_property(ctx.obj):
        handle = Handle.parse(prop.value, HANDLE_PROXY_BASE_URL)
        fields.update({
            'handle__id': str(handle),
            'handle__uri': handle.info_uri,
            'handle_proxied__uri': handle.proxy_url(HANDLE_PROXY_BASE_URL)
        })

    return fields


def find_handle_property(obj: ContentModeledResource) -> RDFDataProperty | None:
    """Find and return the first `RDFDataProperty` in the given object that has
    a datatype of `umdtype:handle` (<http://vocab.lib.umd.edu/datatype#handle>).
    Returns none if no such property can be found."""
    for prop in obj.rdf_properties():
        if isinstance(prop, RDFDataProperty) and prop.datatype == umdtype.handle:
            return prop
    return None

"""
Indexer Name: **`described_by`**

Indexer implementation function: `described_by_field`

Prerequisites: None

Output fields:

| Field               | Python Type | Solr Type |
|---------------------|-------------|-----------|
| `described_by__uri` | `str`       | string    |
"""

from solrizer.indexers import IndexerContext, SolrFields


def described_by_field(ctx: IndexerContext) -> SolrFields:
    """If the resource being indexed has a `description_url` (typically, this is only set
    for non-RDF sources), this indexer uses that value for the `described_by__uri` field.
    Otherwise, it falls back to the `url` on the assumption that the resource is an RDF
    source (i.e., it is self-describing)."""

    return {'described_by__uri': str(ctx.resource.description_url or ctx.resource.url)}

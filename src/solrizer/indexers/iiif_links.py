"""
Indexer Name: **`iiif_links`**

Indexer implementation function: `iiif_links_fields()`

Prerequisites: Must run **after** the [`content_model`](./content_model) indexer

Required config keys:
* `iiif_identifier_prefix`
* `iiif_manifests_url_pattern`
* `iiif_thumbnail_url_pattern`

Output fields:

| Field                                 | Python Type | Solr Type          |
|---------------------------------------|-------------|--------------------|
| `iiif_manifest__id`                   | `str`       | string             |
| `iiif_manifest__uri`                  | `str`       | string             |
| `iiif_thumbnail_identifier__sequence` | `list[str]` | multivalued string |
| `iiif_thumbnail_uri__sequence`        | `list[str]` | multivalued string |
"""

from uritemplate import URITemplate

from solrizer.indexers import IndexerContext, SolrFields
from solrizer.indexers.page_sequence import PageSequence


def iiif_identifier(repo_path: str, prefix: str = '') -> str:
    """Returns a IIIF identifier created by removing a leading slash ("/") in
    `repo_path`, converting the remaining slashes to colons (":"), and finally
    prepend the given `prefix`, if any.

    ```pycon
    >>> iiif_identifier('/foo/bar')
    'foo:bar'
    >>> iiif_identifier('/foo/bar', 'fcrepo:')
    'fcrepo:foo:bar'
    ```
    """
    return prefix + repo_path.lstrip('/').replace('/', ':')


def iiif_links_fields(ctx: IndexerContext) -> SolrFields:
    """Generates links to the IIIF manifest for the indexed resource, as well as
    links to thumbnail images for all pages in that resource. It also includes
    fields with just the IIIF identifier.

    Note that although this uses the `PageSequence` class, this indexer is not
    directly reliant on the `solrizer.indexers.page_sequence` indexer running
    before it runs."""
    manifest_uri_template = URITemplate(ctx.config['iiif_manifests_url_pattern'])
    thumbnail_uri_template = URITemplate(ctx.config['iiif_thumbnail_url_pattern'])

    pages = PageSequence(ctx)
    identifier = iiif_identifier(
        repo_path=ctx.resource.path,
        prefix=ctx.config['iiif_identifier_prefix'],
    )
    thumbnail_identifiers = [
        iiif_identifier(
            repo_path=ctx.repo.endpoint.repo_path(page['pcdmobject__has_file'][0]['id']),
            prefix=ctx.config['iiif_identifier_prefix'],
        )
        for page in pages
    ]
    return {
        'iiif_manifest__id': identifier,
        'iiif_manifest__uri': manifest_uri_template.expand(id=identifier),
        'iiif_thumbnail_identifier__sequence': thumbnail_identifiers,
        'iiif_thumbnail_uri__sequence': [thumbnail_uri_template.expand(id=id) for id in thumbnail_identifiers],
    }

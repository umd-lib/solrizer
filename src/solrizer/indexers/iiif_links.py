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
| `iiif_thumbnail_sequence__ids`        | `list[str]` | multivalued string |
| `iiif_thumbnail_sequence__uris`       | `list[str]` | multivalued string |
"""
from typing import Any

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
    manifest_uri_template = URITemplate(ctx.config['IIIF_MANIFESTS_URL_PATTERN'])
    thumbnail_uri_template = URITemplate(ctx.config['IIIF_THUMBNAIL_URL_PATTERN'])

    pages = ctx.data.get('page_sequence', PageSequence(ctx))
    identifier = iiif_identifier(
        repo_path=ctx.resource.path,
        prefix=ctx.config['IIIF_IDENTIFIER_PREFIX'],
    )
    thumbnail_identifiers = [get_first_file_identifier(ctx, page) for page in pages]
    return {
        'iiif_manifest__id': identifier,
        'iiif_manifest__uri': manifest_uri_template.expand(id=identifier),
        'iiif_thumbnail_sequence__ids': thumbnail_identifiers,
        'iiif_thumbnail_sequence__uris': [thumbnail_uri_template.expand(id=id) for id in thumbnail_identifiers],
    }


def is_preservation_file(file: SolrFields) -> bool:
    """Checks for the presence of `pcdmuse:PreservationMasterFile` in the file
    document's `file__rdf_type__curies` field."""

    return 'pcdmuse:PreservationMasterFile' in file.get('file__rdf_type__curies', [])


def is_image_file(file: SolrFields, mime_subtype: str = None) -> bool:
    """Checks the file document's `file__mime_type__str` field to see if it has
    the "image" type. If the `mime_subtype` is given, the file's MIME type must
    exactly match "image/{mime_subtype}".

    ```pycon
    >>> jpeg_file = {'file__mime_type__str': 'image/jpeg'}
    >>> tiff_file = {'file__mime_type__str': 'image/tiff'}

    >>> is_image_file(jpeg_file)
    True

    >>> is_image_file(tiff_file)
    True

    # subtype must match exactly
    >>> is_image_file(tiff_file, 'jpeg')
    False

    ```
    """

    mime_type = file.get('file__mime_type__str', '')
    if mime_subtype is None:
        return mime_type.startswith('image/')
    else:
        return mime_type == f'image/{mime_subtype}'


def get_best_image_file(page: SolrFields) -> SolrFields:
    """Get the "best" image file document, according to the following order of preference:

    1. First file with RDF type `pcdmuse:PreservationMasterFile` and MIME type matching `image/*`
    2. First file with MIME type `image/tiff`
    3. First file with MIME type `image/jpeg`
    4. First file with MIME type matching `image/*`

    If none of these criteria are satisfied, raises an `ImageUnavailable` exception.
    """
    try:
        files: list[SolrFields] = page['page__has_file']
    except KeyError:
        raise ImageUnavailable

    if preservation_files := [f for f in files if (is_preservation_file(f) and is_image_file(f))]:
        return preservation_files[0]
    if tiff_files := [f for f in files if is_image_file(f, 'tiff')]:
        return tiff_files[0]
    if jpeg_files := [f for f in files if is_image_file(f, 'jpeg')]:
        return jpeg_files[0]
    if image_files := [f for f in files if is_image_file(f)]:
        return image_files[0]

    raise ImageUnavailable


def get_first_file_identifier(ctx: IndexerContext, page: SolrFields) -> str:
    """Given an `IndexerContext` and a page dictionary, returns the IIIF identifier
    for the best file to use as a thumbnail for that page. Returns "static:unavailable"
    if page has no suitable files. See `get_best_image_file()` for the criteria for
    "best" file."""

    try:
        file = get_best_image_file(page)
    except ImageUnavailable:
        return 'static:unavailable'

    file_uri = file['id']
    return iiif_identifier(
        repo_path=ctx.repo.endpoint.repo_path(file_uri),
        prefix=ctx.config['IIIF_IDENTIFIER_PREFIX'],
    )


class ImageUnavailable(Exception):
    pass

"""
Indexer Name: **`page_sequence`**

Indexer implementation function: `page_sequence_fields()`

Prerequisites: Must run **after** the [`content_model`](./content_model) indexer

Output fields:

| Field                       | Python Type | Solr Type                     |
|-----------------------------|-------------|-------------------------------|
| `page_label_sequence__txts` | `list[str]` | multivalued string, tokenized |
| `page_uri_sequence__uris`   | `list[str]` | multivalued string            |
"""
from collections.abc import Iterator
from typing import Any

from plastron.models.ore import Proxy
from plastron.repo import RepositoryError
from plastron.repo.pcdm import PCDMObjectResource

from solrizer.indexers import IndexerContext, SolrFields, IndexerError


def get_members_by_uri(ctx: IndexerContext) -> dict[str, dict]:
    """Create a dictionary mapping member URIs to the members' index documents."""
    member_list: list[dict] = ctx.doc.get('object__has_member', [])
    return {member['id']: member for member in member_list}


class PageSequence:
    """Represents an ordered sequence of members of a resource. Determines
    the ordering by following the `ore:Proxy` chain, starting with the proxy
    resource linked in the resource's `first` property, and continuing along
    the `next` attributes of the proxy resources. The actual member URIs are
    determined from the `proxy_for` property for each proxy, and then the
    member's index document is retrieved from the `members_by_uri` attribute."""
    def __init__(self, ctx: IndexerContext):
        self.ctx: IndexerContext = ctx
        self.members_by_uri: dict[str, dict] = get_members_by_uri(ctx)
        """Mapping of member URI to that member's index document"""
        self._uris = None

    def __iter__(self):
        return iter(self.pages)

    def __getitem__(self, item):
        return self.pages[item]

    def __len__(self):
        return len(self.uris)

    @property
    def pages(self) -> list[SolrFields]:
        """The ordered list of index documents (dictionaries) of pages."""
        return [self.members_by_uri[uri] for uri in self.uris]

    def _build_uri_list(self) -> list[str]:
        pcdm_resource = self.ctx.resource.convert_to(PCDMObjectResource)
        return list(pcdm_resource.get_sequence())

    @property
    def uris(self) -> list[str]:
        """The ordered list of page URIs."""
        if self._uris is None:
            self._uris = self._build_uri_list()
        return self._uris

    @property
    def labels(self) -> list[str]:
        """The ordered list of page labels, taken from the `page__title__txt` field
        of each page. If a page does not have a `page__title__txt` field, uses `[Page N]`,
        where `N` is the position of the page in the sequence."""
        return [str(page.get('page__title__txt', f'[Page {n}]')) for n, page in enumerate(self.pages, 1)]


def page_sequence_fields(ctx: IndexerContext) -> SolrFields:
    """Indexer function that generates `page_label_sequence` and
    `page_uri_sequence` fields."""

    pages = PageSequence(ctx)
    # cache the page sequence for later
    ctx.data['page_sequence'] = pages
    if len(pages) > 0:
        return {
            'page_label_sequence__txts': pages.labels,
            'page_uri_sequence__uris': pages.uris,
        }
    else:
        return {}

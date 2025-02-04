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

from typing import Any, Iterator

from solrizer.indexers import IndexerContext, SolrFields


def follow_sequence(proxy: dict[str, Any]) -> Iterator[str]:
    """Returns an iterator of member URIs, as ordered using the sequence of
    `ore:Proxy` objects. Starting with `proxy`, yield the member URI of the
    target of that proxy (`proxy__proxy_for__uri` field), then recursively
    follow the `proxy__next` link (if present)."""
    target = proxy['proxy__proxy_for__uri']
    yield target
    if 'proxy__next' in proxy:
        yield from follow_sequence(proxy['proxy__next'][0])


def get_members_by_uri(ctx: IndexerContext) -> dict[str, dict]:
    """Create a dictionary mapping member URIs to the members' index documents."""
    member_list: list[dict] = ctx.doc.get(f'{ctx.content_model_prefix}__has_member', [])
    return {member['id']: member for member in member_list}


class PageSequence:
    """Represents an ordered sequence of members of a resource. Determines
    the ordering by following `{content_model}__first` and `proxy__next`
    fields. The actual member URIs are determined from the `proxy__proxy_for__uri`
    field for each proxy, and then the member's index document is retrieved
    from the `members_by_uri` property."""
    def __init__(self, ctx: IndexerContext):
        self.ctx: IndexerContext = ctx
        self.members_by_uri: dict[str, dict] = get_members_by_uri(ctx)
        """Mapping of member URI to that member's index document"""

    def __iter__(self):
        return iter(self.pages)

    def __getitem__(self, item):
        return self.pages[item]

    @property
    def pages(self) -> list[SolrFields]:
        """The ordered list of index documents (dictionaries) of pages."""
        return [self.members_by_uri[uri] for uri in self.uris]

    @property
    def uris(self) -> list[str]:
        """The ordered list of page URIs."""
        try:
            first_proxy: dict[str, Any] = self.ctx.doc[f'{self.ctx.content_model_prefix}__first'][0]
        except (KeyError, IndexError):
            # no proxies found, assuming no page order
            return []
        return [uri for uri in follow_sequence(first_proxy)]

    @property
    def labels(self) -> list[str]:
        """The ordered list of page labels, taken from the `pcdmobject__title__txt`
        field of each page. If a page does not have a `pcdmobject__title__txt`
        field, uses `[Page N]`, where `N` is the position of the page in the
        sequence."""
        return [str(page.get('pcdmobject__title__txt', f'[Page {n}]')) for n, page in enumerate(self.pages, 1)]


def page_sequence_fields(ctx: IndexerContext) -> SolrFields:
    """Indexer function that generates `page_label_sequence` and
    `page_uri_sequence` fields."""

    if f'{ctx.content_model_prefix}__first' not in ctx.doc:
        return {}

    pages = PageSequence(ctx)
    return {
        'page_label_sequence__txts': pages.labels,
        'page_uri_sequence__uris': pages.uris,
    }

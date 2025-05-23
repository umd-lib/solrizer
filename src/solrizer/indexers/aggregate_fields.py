"""
Indexer Name: **`aggregate_fields`**

Indexer implementation function: `aggregate_fields()`

Prerequisites: None, though for maximum usefulness it should be run
toward or at the end of the list of indexers.

Output fields: Defined by the indexer settings.
"""

import logging
from collections import defaultdict

import jq

from solrizer.indexers import IndexerContext, SolrFields, IndexerError

logger = logging.getLogger(__name__)


def aggregate_fields(ctx: IndexerContext) -> SolrFields:
    """Indexer function that adds fields composed of data retrieved by running
    [jq](https://jqlang.org/manual/) queries (using the
    [Python bindings](https://pypi.org/project/jq/)) against the current state
    of the index document.

    Fields to be added are named in the indexer settings. All fields added
    should be multivalued, as this indexer returns lists for all of the fields
    it creates."""

    fields = defaultdict(list)
    try:
        jq_filters = {k: [jq.compile(q) for q in v] for k, v in ctx.settings.items()}
    except ValueError as e:
        raise IndexerError(f'Unable to compile aggregate field query: {e}')

    for field, queries in jq_filters.items():
        logger.info(f'Running queries to build field "{field}"')
        for query in queries:
            logger.debug(f'Query: {query.program_string}')
            fields[field].extend(filter(lambda v: v is not None, iter(query.input_value(ctx.doc))))

    return fields

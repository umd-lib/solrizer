import logging
from collections import defaultdict

import jq

from solrizer.indexers import IndexerContext, SolrFields, IndexerError

logger = logging.getLogger(__name__)


def aggregate_fields(ctx: IndexerContext) -> SolrFields:
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

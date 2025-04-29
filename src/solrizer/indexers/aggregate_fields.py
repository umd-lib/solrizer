from collections import defaultdict

import jq

from solrizer.indexers import IndexerContext, SolrFields, IndexerError


def aggregate_fields(ctx: IndexerContext) -> SolrFields:
    fields = defaultdict(list)
    try:
        jq_filters = {k: [jq.compile(q) for q in v] for k, v in ctx.settings.items()}
    except ValueError as e:
        raise IndexerError(f'Unable to compile aggregate field query: {e}')

    for field, queries in jq_filters.items():
        for query in queries:
            fields[field].extend(filter(lambda v: v is not None, iter(query.input_value(ctx.doc))))

    return fields

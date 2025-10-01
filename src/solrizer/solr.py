import requests

from solrizer.indexers import SolrFields


def create_atomic_update(doc: SolrFields, solr_query_endpoint: str):
    """ Transform the `doc` into an
    [atomic update](https://solr.apache.org/guide/solr/9_6/indexing-guide/partial-document-updates.html#atomic-updates)
    using the `solr_query_endpoint` URL to get the current version of the document
    from the index and running a diff against `doc` to find changed keys."""

    response = requests.get(solr_query_endpoint, params={'ids': doc['id']})
    try:
        old_doc = response.json()['response']['docs'][0]
    except (IndexError, KeyError):
        old_doc = {}

    return atomic_diff(old_doc, doc)


COPY_KEYS = {'id', '_root_'}
"""Copy these keys verbatim into the atomic update."""
SKIP_KEYS = {'_version_'}
"""Skip these keys when creating the atomic update."""


def atomic_diff(old_doc: SolrFields, new_doc: SolrFields) -> dict:
    """Create a Solr atomic update structure based on the changes from the
    `old_doc` to the `new_doc`."""

    diff = {}
    for key in old_doc.keys():
        if key in COPY_KEYS:
            # copy these keys verbatim
            diff[key] = old_doc[key]
        elif key in SKIP_KEYS:
            # ignore these keys
            continue
        elif key not in new_doc:
            # field was removed between old and new doc
            diff[key] = {'set': None}
        else:
            if old_doc[key] == new_doc[key]:
                # no change, ignore
                continue
            else:
                # value of an existing field was updated
                diff[key] = {'set': new_doc[key]}
    for key in filter(lambda k: k not in old_doc, new_doc.keys()):
        # new field
        if key in COPY_KEYS:
            diff[key] = new_doc[key]
        elif key in SKIP_KEYS:
            continue
        else:
            diff[key] = {'set': new_doc[key]}

    return diff

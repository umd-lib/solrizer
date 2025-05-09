"""
Indexer Name: **`facets`**

Indexer implementation function: `facet_fields()`

Prerequisites: None

The `facets` indexer is implemented by a collection of faceter classes in the
`solrizer.faceters` module. Much like the indexers themselves, these classes
are registered as entry points in the `pyproject.toml` project metadata file.
In this case, the group name is `solrizer_faceters`.

Each faceter has a `facet_name` attribute. The final Solr field name is formed
from that value suffixed with "__facet".

Each faceter must implement a `get_values()` method that should either return
a list of strings, or `None` if the object being indexed has no values for the
facet currently being constructed.

Faceters are instantiated with an `IndexerContext` object that is available as
a `ctx` instance attribute. Through this, the faceter can access either the
content modeled resource (`self.ctx.obj`) or the current state of the Solr
document (`self.ctx.doc`), or both, depending on its needs.

Because faceters are configured as entry points, it is possible for packages
external to the Solrizer project to implement their own custom faceters, as
long as they get added to the `solrizer_faceters` entry point group via their
respective `pyproject.toml` files.
"""
import importlib.metadata
import logging

from solrizer.indexers import IndexerContext, SolrFields

logger = logging.getLogger(__name__)


def facet_fields(ctx: IndexerContext) -> SolrFields:
    fields = {}

    available_faceters = importlib.metadata.entry_points(group='solrizer_faceters')
    logger.info(f'Available faceters: {available_faceters}')

    for faceter in (f.load() for f in available_faceters):
        logger.info(f'Running faceter "{faceter.__name__}"')
        if values := faceter(ctx).get_values():
            fields[faceter.facet_name + '__facet'] = values

    return fields

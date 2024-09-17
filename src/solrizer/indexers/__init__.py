"""
Indexers are implemented as functions that take an `IndexerContext` object
as their single argument, and return a dictionary mapping Solr field names
to values. The `IndexerContext` contains, among other things, a dictionary
holding the accumulated output of multiple indexers. This dictionary is
updated after each indexer runs, so later indexers have access to previous
indexers outputs. (Note that there is no way to explicitly specify a
dependency or ordering requirement on indexers, so any such dependencies
will have to be manually reckoned with by the developers of such indexers.)

Indexers are registered using the entry points specification in the
`pyproject.toml` project metadata file, in the group `solrizer_indexers`:

```toml
[project.entry-points.solrizer_indexers]
content_model = "solrizer.indexers.content_model:content_model_fields"
```

The key is the name that will be used later to look up the indexer,
and the value is a `"package.path:function_name"` string.

The indexers are run via the `IndexerContext.run()` instance method. It
takes a list of indexer names to run, and returns the accumulated dictionary
of fields suitable for sending to Solr.

```python
from solrizer.indexers import IndexerContext

ctx = IndexerContext(repo=..., resource=..., model_class=..., doc=...)

doc = ctx.run(['content_model', 'discoverability', 'page_sequence'])
```
"""
import importlib.metadata
import logging
from dataclasses import dataclass
from functools import cached_property
from typing import Iterable, Mapping, Any

from plastron.rdfmapping.resources import RDFResourceBase
from plastron.repo import RepositoryResource, Repository

type SolrFields = dict[str, str | int | list | dict]
"""Type alias for Solr index document dictionaries."""

AVAILABLE_INDEXERS = importlib.metadata.entry_points(group='solrizer_indexers')
"""Available processors determined from the `solrizer_indexers` entry point
group."""

logger = logging.getLogger(__name__)


class IndexerError(Exception):
    """Raised when there is an error during indexer processing."""


@dataclass
class IndexerContext[ModelType: RDFResourceBase]:
    """Holds the necessary context information for indexing a single resource."""
    repo: Repository
    """Source repository of the resource."""
    resource: RepositoryResource
    """The resource being indexed."""
    model_class: type[ModelType]
    """The Plastron content model class of the resource."""
    doc: SolrFields
    """The current state of the Solr index document."""
    config: Mapping[str, Any]
    """Additional configuration."""

    @property
    def content_model_prefix(self) -> str:
        """String used by the `solrizer.indexers.content_model` indexer to
        prefix field names."""
        return self.model_class.__name__.lower()

    @cached_property
    def obj(self) -> ModelType:
        """The `resource`, described using the `model_class`. This is a
        cached property, so repeated calls to it will return the same object."""
        return self.resource.describe(self.model_class)

    def run(self, indexers: Iterable[str]) -> SolrFields:
        """Runs each indexer in the `indexers` iterable, and returns the
        final state of the Solr index document."""
        for name in indexers:
            try:
                indexer = AVAILABLE_INDEXERS[name].load()
            except KeyError as e:
                raise IndexerError(f'No indexer named {e} is registered')

            try:
                self.doc.update(indexer(self))
            except IndexerError as e:
                logger.error(f'Unable to run indexer "{name}": {e}')
                raise

        return self.doc

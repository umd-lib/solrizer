import logging
from typing import Iterable, Callable, Iterator

from plastron.models.authorities import VocabularyTerm
from plastron.namespaces import xsd, umdtype, namespace_manager
from plastron.rdfmapping.properties import RDFDataProperty, RDFObjectProperty, RDFProperty
from plastron.rdfmapping.resources import RDFResource, RDFResourceBase
from plastron.repo import Repository
from rdflib import Literal, URIRef

type SolrDoc = dict[str, str | int | list]

logger = logging.getLogger(__name__)

# field mappings for RDF literals with particular datatypes
FIELD_ARGUMENTS_BY_DATATYPE = {
    # integer types
    xsd.int: {'suffix': '__int', 'converter': int},
    xsd.integer: {'suffix': '__int', 'converter': int},
    xsd.long: {'suffix': '__int', 'converter': int},
    # datetime type
    xsd.dateTime: {'suffix': '__dt'},
    # identifier types
    umdtype.accessionNumber: {'suffix': '__id'},
    umdtype.handle: {'suffix': '__id'},
}
# field mappings for fields with particular property names
FIELD_ARGUMENTS_BY_ATTR_NAME = {
    'date': {'suffix': '__edtf'},
    'identifier': {'suffix': '__id'},
}


def get_model_fields(obj: RDFResourceBase, repo: Repository, prefix: str = '') -> SolrDoc:
    """Iterates over the RDF properties of `obj`, and creates a dictionary of Solr field
    names to values."""
    logger.info(f'Converting {obj.uri}')
    fields = {}
    for prop in obj.rdf_properties():
        if len(prop) == 0:
            # skip properties with no values
            logger.debug(f'Skipping empty property {prop.attr_name}')
            continue
        if isinstance(prop, RDFDataProperty):
            fields.update(get_data_fields(prop, prefix))
        elif isinstance(prop, RDFObjectProperty):
            fields.update(get_object_fields(prop, repo, prefix))

    return fields


def get_linked_objects(prop: RDFObjectProperty, repo: Repository) -> Iterator[RDFResource]:
    for uri in prop.values:
        yield repo[uri].read().describe(prop.object_class)


def get_child_documents(prefix: str, objects: Iterable[RDFResource], repo: Repository) -> list[SolrDoc]:
    return [{'id': str(o.uri), **get_model_fields(o, repo=repo, prefix=prefix)} for o in objects]


def language_suffix(language: str | None) -> str:
    if language is not None:
        return '_' + language.lower().replace('-', '_')
    else:
        return ''


def get_data_fields(prop: RDFDataProperty, prefix: str = '') -> SolrDoc:
    """Get the dictionary of field key(s) and value(s) for the given data
    property using `get_field()`. All keys are prepended with the given
    `prefix`.

    If the property has a datatype found in `FIELD_ARGUMENTS_BY_DATATYPE`,
    the parameters for `get_field()` are taken from there. Similarly, if
    the property has a name found in `FIELD_ARGUMENTS_BY_NAME`, arguments
    are taken from there. Otherwise, the property is treated as text. For
    unique language among the property's values, it creates a key by
    appending "__txt_{language_code}" to the field. For the value(s) that
    have no language code, the suffix is merely "__txt"."""
    if prop.datatype in FIELD_ARGUMENTS_BY_DATATYPE:
        # special handling per datatype
        return get_field(prop, prefix, **FIELD_ARGUMENTS_BY_DATATYPE[prop.datatype])
    else:
        # special handling per property name
        if prop.attr_name in FIELD_ARGUMENTS_BY_ATTR_NAME:
            return get_field(prop, prefix, **FIELD_ARGUMENTS_BY_ATTR_NAME[prop.attr_name])
        else:
            # everything else is treated as text
            fields = {}
            for language in prop.languages:
                fields.update(get_field(
                    prop=prop,
                    prefix=prefix,
                    suffix='__txt' + language_suffix(language),
                    value_filter=lambda v: v.language == language,
                ))
            return fields


def get_object_fields(prop: RDFObjectProperty, repo: Repository, prefix: str = '') -> SolrDoc:
    fields = {}
    fields.update(get_field(prop, prefix, '__uri'))
    fields.update(get_field(prop, prefix, '__curie', converter=shorten_uri))
    if prop.object_class is VocabularyTerm:
        if prop.object is not None:
            # add vocabulary fields
            fields.update(get_model_fields(prop.object, repo=repo, prefix=prefix + prop.attr_name + '__'))
    elif prop.embedded:
        fields[prefix + prop.attr_name] = get_child_documents(
            prefix=prop.object_class.__name__.lower() + '__',
            objects=prop.objects,
            repo=repo,
        )
    elif prop.object_class is not None:
        # linked object
        fields[prefix + prop.attr_name] = get_child_documents(
            prefix=prop.object_class.__name__.lower() + '__',
            objects=get_linked_objects(prop, repo),
            repo=repo,
        )
    return fields


def get_field(
    prop: RDFProperty,
    prefix: str = '',
    suffix: str = '__str',
    converter: Callable[[Literal | URIRef], str | int] = str,
    value_filter: Callable[[Literal | URIRef], bool] = lambda v: True,
) -> SolrDoc:
    """Convert a property to a `{field_name: value(s)}` format dictionary."""
    name = prefix + prop.attr_name + suffix
    values = [converter(v) for v in prop.values if value_filter(v)]
    if prop.repeatable:
        return {name + 's': values}
    else:
        return {name: values[0]}


def shorten_uri(uri: str) -> str | None:
    """Attempt to shorten `uri` into a CURIE with a known prefix. If no
    such prefix is found, returns the full `uri` string. If `uri` is
    `None`, returns `None`."""
    if uri is None:
        return None
    try:
        return namespace_manager.curie(uri, generate=False)
    except (KeyError, ValueError):
        return str(uri)

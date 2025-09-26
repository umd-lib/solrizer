from plastron.models import ContentModeledResource
from plastron.namespaces import dcterms
from plastron.rdfmapping.descriptors import DataProperty
from rdflib import Literal

from solrizer.indexers.content_model import get_resource_language


class ModelWithLanguage(ContentModeledResource):
    language = DataProperty(dcterms.language)


def test_get_resource_language_no_language_property():
    obj = ContentModeledResource()
    assert get_resource_language(obj) is None


def test_get_resource_language_no_value():
    obj = ModelWithLanguage()
    assert get_resource_language(obj) is None


def test_get_resource_language():
    obj = ModelWithLanguage(language=Literal('en'))
    assert get_resource_language(obj) == 'en'


class ModelMitSprache(ContentModeledResource):
    sprache = DataProperty(dcterms.language)


def test_get_resource_language_alternate_prop_name():
    obj = ModelMitSprache(sprache=Literal('de'))
    assert get_resource_language(obj, prop_name='sprache') == 'de'

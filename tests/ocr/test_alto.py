import pytest
from lxml import etree

from solrizer.ocr import XYWH, BBox
from solrizer.ocr.alto import get_scale, ALTOResource


@pytest.mark.parametrize(
    ('unit', 'image_resolution', 'expected_scale'),
    [
        ('inch1200', (400, 400), (1 / 3, 1 / 3)),
        ('mm10', (508, 508), (2.0, 2.0)),
        ('pixel', (300, 300), (1, 1))
    ]
)
def test_get_scale(unit, image_resolution, expected_scale):
    assert get_scale(unit, image_resolution) == expected_scale


def test_unknown_measurement_unit():
    with pytest.raises(ValueError):
        get_scale('BAD_UNIT', (400, 400))


def test_alto_resource(datadir):
    with (datadir / 'alto.xml').open() as fh:
        xmldoc = etree.parse(fh)

    alto = ALTOResource(xmldoc, (400, 400))
    assert len(list(alto.textblocks)) == 2
    assert alto.textblock('NON-EXISTENT IDENTIFIER') is None
    block = alto.textblock('P1_TB00003')
    assert block is not None

    assert block.xywh == XYWH(339, 780, 216, 44)
    assert block.bbox == BBox(339, 780, 555, 824)

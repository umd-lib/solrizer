from collections.abc import Iterator
from typing import NamedTuple, Union, Optional

from lxml import etree
from lxml.etree import ElementTree, Element

from solrizer.ocr import XYWH, BBox

ns = {
    "alto": "http://www.loc.gov/standards/alto/ns-v2#"
}


class Scale(NamedTuple):
    x: float
    y: float


def get_scale(unit: str, image_resolution: tuple[int, int]) -> Scale:
    xres = image_resolution[0]
    yres = image_resolution[1]
    if unit == 'inch1200':
        return Scale(xres / 1200.0, yres / 1200.0)
    elif unit == 'mm10':
        return Scale(xres / 254.0, yres / 254.0)
    elif unit == 'pixel':
        return Scale(1, 1)
    else:
        raise ValueError("Unknown MeasurementUnit " + unit)


class ALTOResource:
    def __init__(self, xmldoc: ElementTree, image_resolution: tuple[int, int]):
        self.xmldoc = xmldoc
        unit = xmldoc.xpath('/alto:alto/alto:Description/alto:MeasurementUnit', namespaces=ns)[0].text
        self.scale = get_scale(unit, image_resolution)

    @property
    def strings(self) -> Iterator['String']:
        for block in self:
            for line in block:
                for inline in line:
                    if isinstance(inline, String):
                        yield inline

    def __iter__(self):
        return self.textblocks

    @property
    def textblocks(self) -> Iterator['TextBlock']:
        for node in self.xmldoc.xpath("//alto:TextBlock", namespaces=ns):
            yield TextBlock(node, self.scale)

    def textblock(self, identifier: str) -> Optional['TextBlock']:
        try:
            return TextBlock(
                self.xmldoc.xpath("//alto:TextBlock[@ID=$id]", id=identifier, namespaces=ns)[0],
                self.scale,
            )
        except IndexError:
            return None


class Region:
    def __init__(self, element: Element, scale: Scale):
        self.element = element
        self.scale = scale
        self.id = self.element.get('ID')
        self._xywh = XYWH(
            x=round(int(self.element.get('HPOS')) * self.scale.x),
            y=round(int(self.element.get('VPOS')) * self.scale.y),
            w=round(int(self.element.get('WIDTH')) * self.scale.x),
            h=round(int(self.element.get('HEIGHT', 0)) * self.scale.y),
        )
        self._bbox = BBox.from_xywh(self._xywh)

    @property
    def xywh(self):
        return self._xywh

    @property
    def bbox(self):
        return self._bbox


class TextBlock(Region):
    def __iter__(self):
        return self.lines

    def __str__(self):
        return '\n'.join(str(s) for s in self.lines)

    @property
    def lines(self) -> Iterator['TextLine']:
        for node in self.element.xpath('alto:TextLine', namespaces=ns):
            yield TextLine(node, self.scale)


class TextLine(Region):
    def __iter__(self):
        return self.inlines

    def __str__(self):
        return ''.join(str(s) for s in self.inlines)

    @property
    def inlines(self) -> Iterator[Union['String', 'Space', 'Hyphen']]:
        for node in self.element.xpath('alto:String|alto:SP|alto:HYP', namespaces=ns):
            tag = etree.QName(node.tag)
            if tag.localname == 'String':
                yield String(node, self.scale)
            elif tag.localname == 'SP':
                yield Space(node, self.scale)
            elif tag.localname == 'HYP':
                yield Hyphen(node, self.scale)


class String(Region):
    def __str__(self):
        return self.content

    @property
    def content(self) -> str:
        # for indexing purposes, if there is a hyphenated word across multiple
        # bounding boxes, we create two tokens, each with the full substituted
        # content (i.e., the unbroken word) and their respective bounding boxes
        if 'SUBS_CONTENT' in self.element.attrib:
            return self.element.get('SUBS_CONTENT')
        else:
            return self.element.get('CONTENT', '')


class Space(Region):
    def __str__(self):
        return ' '


class Hyphen(Region):
    def __str__(self):
        return '\N{SOFT HYPHEN}'

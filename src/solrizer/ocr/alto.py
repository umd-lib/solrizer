from typing import Iterator, Union, Optional

from lxml import etree
from lxml.etree import ElementTree, Element

from solrizer.ocr import XYWH, BBox

ns = {
    "alto": "http://www.loc.gov/standards/alto/ns-v2#"
}


def get_scale(unit: str, image_resolution: tuple[int, int]) -> tuple[float, float]:
    xres = image_resolution[0]
    yres = image_resolution[1]
    if unit == 'inch1200':
        return xres / 1200.0, yres / 1200.0
    elif unit == 'mm10':
        return xres / 254.0, yres / 254.0
    elif unit == 'pixel':
        return 1, 1
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
    def __init__(self, element: Element, scale: tuple[float, float]):
        self.element = element
        self.scale = scale
        self.id = self.element.get('ID')
        self.hpos = int(self.element.get('HPOS'))
        self.vpos = int(self.element.get('VPOS'))
        self.width = int(self.element.get('WIDTH'))
        self.height = int(self.element.get('HEIGHT', 0))

    @property
    def xywh(self):
        xscale = self.scale[0]
        yscale = self.scale[1]
        x = round(self.hpos * xscale)
        y = round(self.vpos * yscale)
        w = round(self.width * xscale)
        h = round(self.height * yscale)

        return XYWH(x, y, w, h)

    @property
    def bbox(self):
        return BBox.from_xywh(self.xywh)


class TextBlock(Region):
    def __iter__(self):
        return self.lines

    @property
    def lines(self) -> Iterator['TextLine']:
        for node in self.element.xpath('alto:TextLine', namespaces=ns):
            yield TextLine(node, self.scale)


class TextLine(Region):
    def __iter__(self):
        return self.inlines

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

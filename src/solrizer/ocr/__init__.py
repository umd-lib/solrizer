from typing import NamedTuple


class XYWH(NamedTuple):
    """Rectangular region defined by its top-left corner (x, y) coordinates
    plus its width and height (w, h).

    ```pycon
    >>> from solrizer.ocr import XYWH

    >>> region = XYWH(100, 120, 50, 60)

    >>> str(region)
    '100,120,50,60'

    ```
    """
    x: int
    """X-axis coordinate of the top-left corner of the region"""
    y: int
    """Y-axis coordinate of the top-left corner of the region"""
    w: int
    """Width of the region (i.e., size along the X-axis)"""
    h: int
    """Height of the region (i.e., size along the Y-axis)"""

    @classmethod
    def from_bbox(cls, bbox: 'BBox'):
        """Creates an `XYWH` object representing the same region as the given
        `BBox` object."""
        return cls(x=bbox.x1, y=bbox.y1, w=bbox.x2 - bbox.x1, h=bbox.y2 - bbox.y1)

    def __str__(self):
        return ','.join(map(str, (self.x, self.y, self.w, self.h)))


class BBox(NamedTuple):
    """Rectangular region defined by its top-left (x1, y1) and bottom-right
    (x2, y2) coordinates.

    ```pycon
    >>> from solrizer.ocr import BBox

    >>> region = BBox(100, 120, 150, 180)

    >>> str(region)
    '100,120,150,180'

    ```
    """
    x1: int
    """X-axis coordinate of the top-left corner of the region"""
    y1: int
    """Y-axis coordinate of the top-left corner of the region"""
    x2: int
    """X-axis coordinate of the bottom-right corner of the region"""
    y2: int
    """Y-axis coordinate of the bottom-right corner of the region"""

    @classmethod
    def from_xywh(cls, xywh: XYWH):
        """Creates a `BBox` object representing the same region as the given
        `XYWH` object."""
        return cls(x1=xywh.x, y1=xywh.y, x2=xywh.x + xywh.w, y2=xywh.y + xywh.h)

    def __str__(self):
        return ','.join(map(str, (self.x1, self.y1, self.x2, self.y2)))

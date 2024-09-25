from typing import NamedTuple


class XYWH(NamedTuple):
    x: int
    y: int
    w: int
    h: int

    @classmethod
    def from_bbox(cls, bbox: 'BBox'):
        return cls(x=bbox.x1, y=bbox.y1, w=bbox.x2 - bbox.x1, h=bbox.y2 - bbox.y1)

    def __str__(self):
        return ','.join(map(str, (self.x, self.y, self.w, self.h)))


class BBox(NamedTuple):
    x1: int
    y1: int
    x2: int
    y2: int

    @classmethod
    def from_xywh(cls, xywh: XYWH):
        return cls(x1=xywh.x, y1=xywh.y, x2=xywh.x + xywh.w, y2=xywh.y + xywh.h)

    def __str__(self):
        return ','.join(map(str, (self.x1, self.y1, self.x2, self.y2)))

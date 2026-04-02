"""
Indexer Name: **`dates`**

Indexer implementation function: `date_fields()`

Prerequisites: Must run **after** the [`content_model`](./content_model) indexer

Output field patterns:

| Field pattern                                     | Python Type | Solr Type      |
|---------------------------------------------------|-------------|----------------|
| `object__{attr}__dt`                              | `str`       | datetime range |
| `object__{attr}__dt_is_uncertain`                 | `bool`      | boolean        |
| `object__{attr}__dt_is_approximate`               | `bool`      | boolean        |
| `object__{attr}__dt_is_uncertain_and_approximate` | `bool`      | boolean        |
| `object__{attr}__dt_precision`                    | `int`       | integer        |
"""

import logging
from datetime import datetime

from edtf import (parse_edtf, Date, UnspecifiedIntervalSection, EDTFObject, UncertainOrApproximate, Interval,
                  Level2Interval, Season, Unspecified, ExponentialYear, LongYear, EDTFParseException, DateAndTime,
                  PartialUncertainOrApproximate, OneOfASet, Consecutives)
from solrizer.indexers import IndexerContext, SolrFields
from solrizer.indexers.utils import solr_datetime

logger = logging.getLogger(__name__)

YMD_STRING = '{0:04d}-{1:02d}-{2:02d}'
"""Formatting string used by `strict_range()` to generate `YYYY-MM-DD` strings."""

PRECISION_VALUES = {
    'day': 6,
    'month': 5,
    'year': 4,
    'decade': 3,
    'century': 2,
    'millennium': 1,
    # the python-edtf module spells "millennium" with only one "n"
    'millenium': 1,
}
"""Mapping of precision-level names to numerical values for sorting."""


def date_fields(ctx: IndexerContext) -> SolrFields:
    """For any EDTF field in the index document (i.e., one whose name ends
    with `__edtf`) creates a corresponding `__dt` field with a value that
    is parseable by Solr as a date or date range. Also, populates four other
    fields:

    * three boolean flag fields with the suffixes `__dt_is_uncertain`,
      `__dt_is_approximate`,and `__dt_is_uncertain_and_approximate` that
      indicate whether the EDTF string had the markers for uncertainty (`?`),
      approximation (`~`), or both (`%`).
    * an integer field with the suffix `__dt_precision__int` to capture the
      precision of the original EDTF date

    Emits a warning and skips any EDTF fields that cannot be represented
    as Solr dates (e.g., exponential years, years with more than four digits),
    or that cannot even be parsed as EDTF strings."""

    # EDTF fields
    for edtf_name in filter(lambda n: n.endswith('__edtf'), ctx.doc.keys()):
        edtf_string = ctx.doc[edtf_name]
        name = edtf_name.replace('__edtf', '')
        try:
            edtf: EDTFObject = parse_edtf(str(edtf_string))
            return {
                name + '__dt': solr_date(edtf),
                name + '__dt_is_uncertain': edtf.is_uncertain,
                name + '__dt_is_approximate': edtf.is_approximate,
                name + '__dt_is_uncertain_and_approximate': edtf.is_uncertain_and_approximate,
                name + '__dt_precision__int': get_precision(edtf),
            }
        except UnsupportedEDTFValue as e:
            logger.warning(f'Cannot convert "{edtf_string}" in field {edtf_name} to a Solr date: {e.reason}')
        except EDTFParseException:
            logger.warning(f'Cannot parse "{edtf_string}" in field {edtf_name} as an EDTF string')
    else:
        return {}


def strict_range(edtf: EDTFObject) -> str:
    """Format the given EDTF date as a Solr date range, using the strict
    upper and lower bounds of the EDTF date."""

    begin = YMD_STRING.format(*edtf.lower_strict()[:3])
    end = YMD_STRING.format(*edtf.upper_strict()[:3])
    return f'[{begin} TO {end}]'


def solr_date(edtf_value: str | EDTFObject, partial_ua_method: str = 'lower_strict') -> str:
    """Convert an EDTF string (or an already parsed `EDTFObject`) into
    a date or date range string valid for Solr.

    Raises an `UnsupportedEDTFValue` exception if the `edtf_value` cannot
    be parsed or cannot be represented as a Solr datetime range."""

    if isinstance(edtf_value, EDTFObject):
        edtf = edtf_value
    else:
        edtf = parse_edtf(edtf_value)

    match edtf:
        case ExponentialYear():
            if abs(int(edtf.exponent)) > 3:
                raise UnsupportedEDTFValue(
                    edtf=edtf,
                    reason='Solr does not support years outside the range -9999 to 9999',
                )
            else:
                return strict_range(edtf)
        case LongYear():
            raise UnsupportedEDTFValue(
                edtf=edtf,
                reason='Solr does not support years outside the range -9999 to 9999',
            )
        case Season() | Unspecified():
            return strict_range(edtf)
        case UnspecifiedIntervalSection():
            return '*'
        case Level2Interval():
            lower = edtf.lower
            upper = edtf.upper
            return f'[{solr_date(lower, 'lower_strict')} TO {solr_date(upper, 'upper_strict')}]'
        case Interval():
            lower = edtf.lower
            upper = edtf.upper
            return f'[{solr_date(lower)} TO {solr_date(upper)}]'
        case UncertainOrApproximate():
            return str(edtf.date)
        case PartialUncertainOrApproximate():
            time_data = getattr(edtf, partial_ua_method)()
            return str(datetime(*time_data[:7]).date())
        case Date():
            return str(edtf)
        case DateAndTime():
            return solr_datetime(str(edtf))
        case _:
            raise UnsupportedEDTFValue(edtf=edtf)


def get_precision(edtf: EDTFObject) -> int | None:
    """Determine the precision of the given EDTF object and return the
    equivalent numerical value taken from `PRECISION_VALUES`."""
    match edtf:
        case UncertainOrApproximate():
            return get_precision(edtf.date)
        case OneOfASet():
            precisions = []
            for obj in edtf.objects:
                precisions.extend(_get_upper_and_lower_precisions(obj))
            return min(precisions) if precisions else None
        case Interval():
            precisions = _get_upper_and_lower_precisions(edtf)
            return min(precisions) if precisions else None
        case Season():
            # TODO: what should season precision be?
            return None
        case Date() | UnspecifiedIntervalSection():
            return PRECISION_VALUES[edtf.precision]
        case _:
            return None


def _get_upper_and_lower_precisions(edtf: Interval | Consecutives):
    precisions = [
        get_precision(edtf.lower),
        get_precision(edtf.upper),
    ]
    return [p for p in precisions if p is not None]


class UnsupportedEDTFValue(ValueError):
    """Raised to indicate this is a valid EDTF string, but one that is not
    translatable into a Solr date or date range."""

    def __init__(self, *args, edtf: EDTFObject, reason: str = 'Solr does not support this EDTF value'):
        super().__init__(*args)
        self.edtf: EDTFObject = edtf
        """The unsupported EDTF object"""
        self.reason: str = reason
        """The reason this `edtf` cannot be represented in Solr"""

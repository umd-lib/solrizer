from collections.abc import Iterable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from edtf import EDTFParseException, parse_edtf
from markdown_to_data import Markdown
from plastron.models import ContentModeledResource
from plastron.repo import Repository, RepositoryResource

from solrizer.indexers import IndexerContext
from solrizer.indexers.dates import UnsupportedEDTFValue, date_fields, solr_date, get_precision

DOCS_DIR = Path(__file__).parents[2] / 'docs'


def get_values(params: dict[str, str | int | None]) -> list[str | int | bool | None]:
    values = []
    for k, v in params.items():
        if k.endswith('?'):
            values.append(bool(v))
        elif isinstance(v, int):
            values.append(v)
        elif isinstance(v, str):
            values.append(v.removeprefix('`').removesuffix('`'))
        else:
            values.append(None)
    return values


def has_columns(table: dict[str, str], columns: Iterable[str]) -> bool:
    return all(c in table for c in columns)


def get_param_set_from_markdown(file: Path, columns: Iterable[str]) -> list[tuple[str, ...]]:
    md = Markdown(file.read_text())
    tables = [t['table'] for t in md.md_list if 'table' in t and has_columns(t['table'], columns)]
    param_set = []
    for table in tables:
        rows = list(zip(*(table[c] for c in columns)))
        data = list(dict(zip(columns, row)) for row in rows)
        for params in data:
            param_set.append(tuple(get_values(params)))
    return param_set


EDTF_TEST_STRINGS = get_param_set_from_markdown(
    file=(DOCS_DIR / 'EDTFtoDateRange.md'),
    columns=['EDTF', 'Solr DateRange'],
)

QUALIFIED_EDTF_TEST_STRINGS = get_param_set_from_markdown(
    file=(DOCS_DIR / 'EDTFtoDateRange.md'),
    columns=['EDTF', 'Solr DateRange', 'Uncertain?', 'Approximate?', 'Uncertain and Approximate?', 'Precision'],
)

UNSUPPORTED_EDTF_STRINGS = [
    # LongYear
    'Y21000',
    'Y-18000',
    # ExponentialYear
    'Y1E5',
    'Y-2E6',
]

INVALID_EDTF_STRINGS = [
    'Y1999-12-31',
    'FAKE',
]


@pytest.fixture
def context_with_date():
    def _context(edtf_value):
        return IndexerContext(
            repo=MagicMock(spec=Repository),
            resource=MagicMock(spec=RepositoryResource),
            model_class=ContentModeledResource,
            doc={
                'date__edtf': edtf_value,
            },
            config={},
        )

    return _context


@pytest.mark.parametrize(
    ('edtf_value', 'expected_solr_value'),
    EDTF_TEST_STRINGS,
)
def test_solr_date(edtf_value, expected_solr_value):
    assert solr_date(edtf_value) == expected_solr_value


@pytest.mark.parametrize(
    ('edtf_value', 'expected_solr_value'),
    EDTF_TEST_STRINGS,
)
def test_date_fields(edtf_value, expected_solr_value, context_with_date):
    fields = date_fields(context_with_date(edtf_value))
    assert fields['date__dt'] == expected_solr_value


@pytest.mark.parametrize(
    (
        'edtf_value',
        'expected_solr_value',
        'is_uncertain',
        'is_approximate',
        'is_uncertain_and_approximate',
        'precision',
    ),
    QUALIFIED_EDTF_TEST_STRINGS,
)
def test_uncertain_and_or_approximate(
    edtf_value,
    expected_solr_value,
    is_uncertain,
    is_approximate,
    is_uncertain_and_approximate,
    precision,
    context_with_date,
):
    expected_fields = {
        'date__dt': expected_solr_value,
        'date__dt_is_uncertain': is_uncertain,
        'date__dt_is_approximate': is_approximate,
        'date__dt_is_uncertain_and_approximate': is_uncertain_and_approximate,
        'date__dt_precision__int': precision,
    }
    assert date_fields(context_with_date(edtf_value)) == expected_fields


@pytest.mark.parametrize(
    'edtf_value',
    UNSUPPORTED_EDTF_STRINGS,
)
def test_unsupported_edtf_solr_date(edtf_value):
    with pytest.raises(UnsupportedEDTFValue):
        solr_date(edtf_value)


@pytest.mark.parametrize(
    'edtf_value',
    UNSUPPORTED_EDTF_STRINGS,
)
def test_unsupported_edtf_date_fields(edtf_value, context_with_date, caplog):
    fields = date_fields(context_with_date(edtf_value))
    assert fields == {}
    assert f'Cannot convert "{edtf_value}"' in caplog.text


@pytest.mark.parametrize(
    'edtf_value',
    INVALID_EDTF_STRINGS,
)
def test_edtf_parse_exception_solr_date(edtf_value):
    with pytest.raises(EDTFParseException):
        solr_date(edtf_value)


@pytest.mark.parametrize(
    'edtf_value',
    INVALID_EDTF_STRINGS,
)
def test_edtf_parse_exception_solr_date(edtf_value, context_with_date, caplog):
    fields = date_fields(context_with_date(edtf_value))
    assert fields == {}
    assert f'Cannot parse "{edtf_value}"' in caplog.text


@pytest.mark.parametrize(
    'edtf_value',
    [
        # LongYear
        'Y21000',
        'Y-18000',
        # ExponentialYear
        'Y1E5',
        'Y-2E6',
        # EDTF parse errors
        'Y-12000/1982',
    ],
)
def test_unsupported_edtf_returns_nothing(edtf_value, context_with_date):
    fields = date_fields(context_with_date(edtf_value))
    assert 'date__dt' not in fields


@pytest.mark.parametrize(
    ('edtf_value', 'expected_precision'),
    [
        ('2026-03-12', 6),
        ('2026-03', 5),
        ('2026', 4),
        ('202X', 3),
        ('20XX', 2),
        ('2XXX', 1),
        ('2026-03-01/2026-03-10', 6),
        ('2026-04/2026-04', 5),
        ('2026/2028', 4),
        ('198X/199X', 3),
        ('19XX/20XX', 2),
        ('1XXX/2XXX', 1),
        ('2026-03/2026-03-10', 5),
        ('2026/2026-03-10', 4),
        ('202X/2026-03-10', 3),
        ('20XX/2026-03-10', 2),
        ('2XXX/2026-03-10', 1),
        ('1990-01-01/1999-02-01', 6),
        ('1990-01-01/1999-02', 5),
        ('1990-01-01/1999', 4),
        ('1990-01-01/199X', 3),
        ('1990-01-01/19XX', 2),
        ('1990-01-01/1XXX', 1),
        ('2026-03-12/', 6),
        ('2026-03/', 5),
        ('2026/', 4),
        ('[2026-03-12..]', 6),
        ('[2026-03..]', 5),
        ('[2026..]', 4),
        ('/2026-03-12', 6),
        ('/2026-03', 5),
        ('/2026', 4),
        ('[..2026-03-12]', 6),
        ('[..2026-03]', 5),
        ('[..2026]', 4),
    ]
)
def test_get_precision(edtf_value, expected_precision):
    assert get_precision(parse_edtf(edtf_value)) == expected_precision

from collections.abc import Iterable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from edtf import EDTFParseException
from markdown_to_data import Markdown
from plastron.models import ContentModeledResource
from plastron.repo import Repository, RepositoryResource

from solrizer.indexers import IndexerContext
from solrizer.indexers.dates import UnsupportedEDTFValue, date_fields, solr_date


DOCS_DIR = Path(__file__).parents[2] / 'docs'


def strip_backticks(quoted: str) -> str:
    return quoted.removeprefix('`').removesuffix('`')


def has_columns(table: dict[str, str], columns: Iterable[str]) -> bool:
    return all(c in table for c in columns)


def get_param_set_from_markdown(file: Path, columns: Iterable[str]) -> list[tuple[str, ...]]:
    md = Markdown(file.read_text())
    tables = [t['table'] for t in md.md_list if 'table' in t and has_columns(t['table'], columns)]
    param_set = []
    for table in tables:
        param_set.extend(
            tuple(map(strip_backticks, params))
            for params in list(zip(*(table[c] for c in columns)))
        )
    return param_set


EDTF_TEST_STRINGS = get_param_set_from_markdown(
    file=(DOCS_DIR / 'EDTFtoDateRange.md'),
    columns=['EDTF', 'Solr DateRange'],
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
    ('edtf_value', 'expected_solr_value', 'is_uncertain', 'is_approximate', 'is_uncertain_and_approximate'),
    [
        ('2024?', '2024', True, False, False),
        ('2024~', '2024', False, True, False),
        ('2024%', '2024', False, False, True),
        ('2024?/2025', '[2024 TO 2025]', True, False, False),
        ('2024~/2025', '[2024 TO 2025]', False, True, False),
        ('2024%/2025', '[2024 TO 2025]', False, False, True),
        ('2024?/2025?', '[2024 TO 2025]', True, False, False),
        ('2024~/2025~', '[2024 TO 2025]', False, True, False),
        ('2024%/2025%', '[2024 TO 2025]', False, False, True),
        ('2024/2025?', '[2024 TO 2025]', True, False, False),
        ('2024/2025~', '[2024 TO 2025]', False, True, False),
        ('2024/2025%', '[2024 TO 2025]', False, False, True),
        ('2024?/2025~', '[2024 TO 2025]', True, True, False),
        ('2024~/2025?', '[2024 TO 2025]', True, True, False),
        ('2024?/2025%', '[2024 TO 2025]', True, False, True),
        ('2024~/2025%', '[2024 TO 2025]', False, True, True),
        # qualified individual components
        ('~1945/1959', '[1945-01-01 TO 1959]', False, True, False),
        ('1945/~1959', '[1945 TO 1959-12-31]', False, True, False),
        ('1945-~06/1959', '[1945-06-01 TO 1959]', False, True, False),
        ('1945/1959~-06', '[1945 TO 1959-06-30]', False, True, False),
        ('1945-06~-15/1959', '[1945-06-15 TO 1959]', False, True, False),
        ('1945/1959-06-~15', '[1945 TO 1959-06-15]', False, True, False),
    ],
)
def test_uncertain_and_or_approximate(
    edtf_value,
    expected_solr_value,
    is_uncertain,
    is_approximate,
    is_uncertain_and_approximate,
    context_with_date,
):
    expected_fields = {
        'date__dt': expected_solr_value,
        'date__dt_is_uncertain': is_uncertain,
        'date__dt_is_approximate': is_approximate,
        'date__dt_is_uncertain_and_approximate': is_uncertain_and_approximate,
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

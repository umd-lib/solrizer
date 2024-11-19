from unittest.mock import MagicMock

import pytest
from edtf import EDTFParseException
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryResource

from solrizer.indexers import IndexerContext
from solrizer.indexers.dates import UnsupportedEDTFValue, date_fields, solr_date

EDTF_TEST_STRINGS = [
    ('1605-11-05', '1605-11-05'),
    ('2000-11', '2000-11'),
    ('1984', '1984'),
    ('2000-11-01/2014-12-01', '[2000-11-01 TO 2014-12-01]'),
    ('2004-06/2006-08', '[2004-06 TO 2006-08]'),
    ('1964/2008', '[1964 TO 2008]'),
    ('2014/2014-12-01', '[2014 TO 2014-12-01]'),
    ('../1985-04-12', '[* TO 1985-04-12]'),
    ('../1985-04', '[* TO 1985-04]'),
    ('../1985', '[* TO 1985]'),
    ('1985-04-12/..', '[1985-04-12 TO *]'),
    ('1985-04/..', '[1985-04 TO *]'),
    ('1985/..', '[1985 TO *]'),
    ('-0009', '-0009'),
    # date and time
    # normalize to UTC (with the "Z" notation)
    ('2024-11-18T11:49:32-05:00', '2024-11-18T16:49:32Z'),
    # seasons, with hemisphere
    # Note about year-wrapping (taken from a comment in edtf.appsettings):
    #
    # > winter in the northern hemisphere wraps the end of the year, so
    # > Winter 2010 could wrap into 2011.
    # > For simplicity, we assume it falls at the end of the year, esp since the
    # > spec says that sort order goes spring > summer > autumn > winter
    # northern hemisphere
    # spring
    ('2001-25', '[2001-03-01 TO 2001-05-31]'),
    # summer
    ('2001-26', '[2001-06-01 TO 2001-08-31]'),
    # autumn
    ('2001-27', '[2001-09-01 TO 2001-11-30]'),
    # winter
    ('2001-28', '[2001-12-01 TO 2001-12-31]'),
    # southern hemisphere
    # spring
    ('2001-29', '[2001-09-01 TO 2001-11-30]'),
    # summer
    ('2001-30', '[2001-12-01 TO 2001-12-31]'),
    # autumn
    ('2001-31', '[2001-03-01 TO 2001-05-31]'),
    # winter
    ('2001-32', '[2001-06-01 TO 2001-08-31]'),
    # other year subdivisions
    # quarters (3-month blocks)
    ('2001-33', '[2001-01-01 TO 2001-03-31]'),
    ('2001-34', '[2001-04-01 TO 2001-06-30]'),
    ('2001-35', '[2001-07-01 TO 2001-09-30]'),
    ('2001-36', '[2001-10-01 TO 2001-12-31]'),
    # quadrimesters (4-month blocks)
    ('2001-37', '[2001-01-01 TO 2001-04-30]'),
    ('2001-38', '[2001-05-01 TO 2001-08-31]'),
    ('2001-39', '[2001-09-01 TO 2001-12-31]'),
    # semesters (6-month blocks)
    ('2001-40', '[2001-01-01 TO 2001-06-30]'),
    ('2001-41', '[2001-07-01 TO 2001-12-31]'),
    # unspecified digits
    ('1992-09-XX', '[1992-09-01 TO 1992-09-30]'),
    ('1992-XX', '[1992-01-01 TO 1992-12-31]'),
    ('199X', '[1990-01-01 TO 1999-12-31]'),
    ('19XX', '[1900-01-01 TO 1999-12-31]'),
    ('1XXX', '[1000-01-01 TO 1999-12-31]'),
    ('XXXX', '[0000-01-01 TO 9999-12-31]'),
    # exponential years, as long as they are between -9999 and 9999
    ('Y1E3', '[1000-01-01 TO 1000-12-31]'),
    ('Y5E2', '[0500-01-01 TO 0500-12-31]'),
    ('Y6E1', '[0060-01-01 TO 0060-12-31]'),
    ('Y-1E3', '[-1000-01-01 TO -1000-12-31]'),
    ('Y-5E2', '[-500-01-01 TO -500-12-31]'),
    ('Y-6E1', '[-060-01-01 TO -060-12-31]'),
]

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
            model_class=RDFResource,
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

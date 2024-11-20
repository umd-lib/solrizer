import pytest

from solrizer.indexers.utils import solr_datetime


@pytest.mark.parametrize(
    'dt_string',
    [
        '2024',
        '2024-11',
        'NOT A DATE',
    ]

)
def test_solr_datetime_invalid_strings(dt_string):
    with pytest.raises(ValueError):
        solr_datetime(dt_string)


@pytest.mark.parametrize(
    ('dt_string', 'expected_value'),
    [
        ('2024-11-19', '2024-11-19T00:00:00Z'),
        ('2024-11-19T09', '2024-11-19T09:00:00Z'),
        ('2024-11-19T09:17', '2024-11-19T09:17:00Z'),
        ('2024-11-19T09:17:32', '2024-11-19T09:17:32Z'),
        ('2024-11-19T09:17:32-08:00', '2024-11-19T17:17:32Z'),
        ('2024-11-19T09:17:32+00:00', '2024-11-19T09:17:32Z'),
    ]
)
def test_solr_datetime(dt_string, expected_value):
    assert solr_datetime(dt_string) == expected_value

import json

import httpretty
import pytest

from solrizer.solr import atomic_diff, create_atomic_update


@pytest.mark.parametrize(
    ('old_doc', 'new_doc', 'expected_diff'),
    [
        # no changes
        (
            {'id': 'foo', 'object__title__txt': 'Foo'},
            {'id': 'foo', 'object__title__txt': 'Foo'},
            {'id': 'foo'},
        ),
        # new value for existing field
        (
            {'id': 'foo', 'object__title__txt': 'Foo'},
            {'id': 'foo', 'object__title__txt': 'Bar'},
            {'id': 'foo', 'object__title__txt': {'set': 'Bar'}},
        ),
        # new value for existing field, skip "_version_"
        (
            {'id': 'foo', '_version_': 1234, 'object__title__txt': 'Foo'},
            {'id': 'foo', 'object__title__txt': 'Bar'},
            {'id': 'foo', 'object__title__txt': {'set': 'Bar'}},
        ),
        # remove one field, add another
        (
            {'id': 'foo', 'object__title__txt': 'Foo'},
            {'id': 'foo', 'object__title__txt_en': 'Bar'},
            {
                'id': 'foo',
                'object__title__txt': {'set': None},
                'object__title__txt_en': {'set': 'Bar'},
            },
        ),
        # update values in nested documents
        (
            {
                'id': 'foo',
                'title': 'Moonpig',
                'pages': [
                    {'id': 'p1', '_root_': 'foo', 'title': 'Page I'},
                    {'id': 'p2', '_root_': 'foo', 'title': 'Page 2'},
                ]
            },
            {
                'id': 'foo',
                'title': 'Moonpig',
                'pages': [
                    {'id': 'p1', '_root_': 'foo', 'title': 'Page I'},
                    {'id': 'p2', '_root_': 'foo', 'title': 'Page II'},
                ]
            },
            {
                'id': 'foo',
                'pages': {
                    'set': [
                        {'id': 'p1', '_root_': 'foo', 'title': 'Page I'},
                        {'id': 'p2', '_root_': 'foo', 'title': 'Page II'},
                    ],
                },
            }
        )
    ]
)
def test_atomic_diff(old_doc, new_doc, expected_diff):
    assert atomic_diff(old_doc, new_doc) == expected_diff


@httpretty.activate()
def test_create_atomic_update_no_old_doc(register_uri_for_reading):
    register_uri_for_reading(
        uri='http://solr.example.com/fcrepo/select',
        content_type='application/json',
        body=json.dumps({'response': {'docs': []}}),
    )
    new_doc = {'id': 'foo', 'title': 'Foo'}
    atomic_update = create_atomic_update(
        new_doc,
        solr_query_endpoint='http://solr.example.com/fcrepo/select',
    )
    assert atomic_update == {'id': 'foo', 'title': {'set': 'Foo'}}

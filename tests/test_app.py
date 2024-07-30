def test_doc_no_uri(client):
    response = client.get('/doc')
    assert response.status_code == 400
    assert response.content_type == 'application/problem+json'
    detail = response.json
    assert detail['status'] == 400
    assert detail['title'] == 'No resource requested'
    assert detail['details'] == 'No resource URL or path was provided as part of this request.'


def test_doc(client):
    response = client.get('/doc?uri=http://example.com/fcrepo/foo')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    result = response.json
    assert result['id'] == 'http://example.com/fcrepo/foo'

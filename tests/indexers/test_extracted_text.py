from pathlib import Path
from unittest.mock import MagicMock

import pytest
from plastron.namespaces import pcdmuse
from plastron.repo.pcdm import PCDMObjectResource

from solrizer.indexers import IndexerError
from solrizer.indexers.extracted_text import get_page_text, PageText


class MockBinaryResource:
    def __init__(self, file: Path):
        self.file = file

    def open(self):
        return self.file.open(mode='rb')


def test_page_text_class():
    page_text = PageText('foo bar', page_index=1, tagged=False)
    assert page_text.text == 'foo bar'
    assert page_text.page_index == 1
    assert not page_text.tagged
    assert str(page_text) == 'foo bar'


def test_get_page_text_plain(datadir):
    def _get_file(mime_type):
        return MockBinaryResource(datadir / 'text.txt') if mime_type == 'text/plain' else None

    mock_resource = MagicMock(spec=PCDMObjectResource)
    mock_resource.get_file = _get_file
    page_text = get_page_text(mock_resource, 0)
    assert page_text.text == 'This is a test, sample, and\nstand-in for a plain text\nOCR file.\n'
    assert page_text.page_index == 0
    assert not page_text.tagged


def test_get_page_text_html(datadir):
    def _get_file(mime_type):
        return MockBinaryResource(datadir / 'text.html') if mime_type == 'text/html' else None

    mock_resource = MagicMock(spec=PCDMObjectResource)
    mock_resource.get_file = _get_file
    page_text = get_page_text(mock_resource, 0)
    assert page_text.text == '\nThis is a test, sample, and\nstand-in for an HTML file\n(with some text)\n'
    assert page_text.page_index == 0
    assert not page_text.tagged


def test_get_page_text_alto(datadir, monkeypatch):
    mock_resource = MagicMock(spec=PCDMObjectResource)

    def mock_get_file(rdf_type=None, **_kwargs):
        if rdf_type == pcdmuse.ExtractedText:
            return datadir / 'alto.xml'
        elif rdf_type == pcdmuse.PreservationMasterFile:
            return MockBinaryResource(datadir / '0002.tif')
        else:
            return None

    mock_resource.get_file.side_effect = mock_get_file

    expected_text = (
        'Vol.|n=0&xywh=339,781,112,41'
        ' VI|n=0&xywh=488,780,66,43'
        ' VARSITY|n=0&xywh=340,926,246,83'
        ' BASKETERS|n=0&xywh=631,920,339,85'
    )
    page_text = get_page_text(mock_resource, 0)
    assert page_text.text == expected_text
    assert page_text.page_index == 0
    assert page_text.tagged


def test_unsupported_xml_ocr_format(datadir):
    mock_resource = MagicMock(spec=PCDMObjectResource)

    def mock_get_file(rdf_type=None, **_kwargs):
        if rdf_type == pcdmuse.ExtractedText:
            return datadir / 'other.xml'
        elif rdf_type == pcdmuse.PreservationMasterFile:
            return MockBinaryResource(datadir / '0002.tif')
        else:
            return None

    mock_resource.get_file.side_effect = mock_get_file
    with pytest.raises(IndexerError):
        get_page_text(mock_resource, 0)


def test_no_preservation_master(datadir):
    mock_resource = MagicMock(spec=PCDMObjectResource)

    def mock_get_file(rdf_type=None, **_kwargs):
        if rdf_type == pcdmuse.ExtractedText:
            return datadir / 'alto.xml'
        else:
            return None

    mock_resource.get_file.side_effect = mock_get_file
    with pytest.raises(IndexerError):
        get_page_text(mock_resource, 0)

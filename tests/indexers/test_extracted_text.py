from pathlib import Path
from unittest.mock import MagicMock

import pytest
from plastron.namespaces import pcdmuse
from plastron.repo.pcdm import PCDMObjectResource

from solrizer.indexers import IndexerError
from solrizer.indexers.extracted_text import get_text_page, PageText, get_text_pages


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
    def _get_file(mime_type=None, rdf_type=None):
        return MockBinaryResource(datadir / 'text.txt') if mime_type == 'text/plain' else None

    mock_resource = MagicMock(spec=PCDMObjectResource)
    mock_resource.get_file = _get_file
    page_text = get_text_page(mock_resource, 0)
    assert page_text.text == 'This is a test, sample, and\nstand-in for a plain text\nOCR file.\n'
    assert page_text.page_index == 0
    assert not page_text.tagged


def test_get_page_text_html(datadir):
    def _get_file(mime_type=None, rdf_type=None):
        return MockBinaryResource(datadir / 'text.html') if mime_type == 'text/html' else None

    mock_resource = MagicMock(spec=PCDMObjectResource)
    mock_resource.get_file = _get_file
    page_text = get_text_page(mock_resource, 0)
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
    page_text = get_text_page(mock_resource, 0)
    assert page_text.text == expected_text
    assert page_text.page_index == 0
    assert page_text.tagged


def test_get_page_text_hocr(datadir, monkeypatch):
    mock_resource = MagicMock(spec=PCDMObjectResource)

    def mock_get_file(rdf_type=None, **_kwargs):
        if rdf_type == pcdmuse.ExtractedText:
            return datadir / 'sample.hocr'
        elif rdf_type == pcdmuse.PreservationMasterFile:
            return MockBinaryResource(datadir / 'litmss-077848-0002.tif')
        else:
            return None

    mock_resource.get_file.side_effect = mock_get_file
    expected_text = (
        ' |n=0&xywh=0,2924,282,1320 '
        ' |n=0&xywh=0,0,404,404 '
        'Page|n=0&xywh=340,473,230,85 '
        '1|n=0&xywh=675,472,77,84 '
        'Additions|n=0&xywh=1238,436,526,159 '
        ':|n=0&xywh=1773,485,71,100 '
        'nd|n=0&xywh=1850,406,154,127 '
        'g¢orrections|n=0&xywh=2055,395,656,161 '
        'for|n=0&xywh=2788,433,164,118 '
        'the|n=0&xywh=3028,425,164,96 '
        'manuseript|n=0&xywh=3312,420,596,108 '
        'of|n=0&xywh=3980,412,112,94 '
        '"The|n=0&xywh=1725,663,219,75 '
        'Future|n=0&xywh=2007,658,355,100 '
        'Is|n=0&xywh=2435,654,111,80 '
        'Now!|n=0&xywh=2607,654,224,74 '
        'A|n=0&xywh=3690,692,26,25 '
        'By|n=0&xywh=2235,762,129,86 '
        'Ka|n=0&xywh=2429,757,101,74 '
        'atherine|n=0&xywh=2497,696,446,192 '
        'Anne|n=0&xywh=3029,761,226,63 '
        'forter|n=0&xywh=3324,738,346,86 '
        ' |n=0&xywh=3443,909,959,151'
    )
    page_text = get_text_page(mock_resource, 0)
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
        get_text_page(mock_resource, 0)


def test_no_preservation_master(datadir):
    mock_resource = MagicMock(spec=PCDMObjectResource)

    def mock_get_file(rdf_type=None, **_kwargs):
        if rdf_type == pcdmuse.ExtractedText:
            return datadir / 'alto.xml'
        else:
            return None

    mock_resource.get_file.side_effect = mock_get_file
    with pytest.raises(IndexerError):
        get_text_page(mock_resource, 0)


def test_page_with_no_files():
    mock_resource = MagicMock(spec=PCDMObjectResource)

    def mock_get_file(_rdf_type=None, **_kwargs):
        return None

    mock_resource.get_file.side_effect = mock_get_file
    text_page = get_text_page(mock_resource, 0)
    assert text_page is None


def test_pages_with_no_files():
    mock_resource = MagicMock(spec=PCDMObjectResource)
    mock_page = MagicMock(spec=PCDMObjectResource)

    def mock_get_file(_rdf_type=None, **_kwargs):
        return None

    mock_page.get_file.side_effect = mock_get_file
    mock_resource.get_sequence.return_value = [mock_page, mock_page]

    pages = get_text_pages(mock_resource)
    assert len(pages) == 0

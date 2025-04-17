"""
Indexer Name: **`extracted_text`**

Indexer implementation function: `extracted_text_fields()`

Prerequisites: None

Output fields:

| Field              | Python Type | Solr Type                                    |
|--------------------|-------------|----------------------------------------------|
| `content__dps_txt` | `str`       | tokenized text with delimited string payload |
"""
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from plastron.namespaces import pcdmuse
from plastron.ocr import OCRResource, ImageWithOCR, UnrecognizedOCRFormatError, ImageFileError
from plastron.repo.pcdm import PCDMObjectResource, PCDMFileBearingResource, AggregationResource

from solrizer.indexers import IndexerContext, SolrFields, IndexerError


@dataclass
class PageText:
    """The textual content of a page. Stringifies to the value of `text`."""

    text: str
    """The content"""
    page_index: int
    """0-based index for this page within its source sequence"""
    tagged: bool = False
    """Flag indicating whether there are bounding box tags
    included in the `text` string."""

    def __str__(self):
        return self.text


def extracted_text_fields(ctx: IndexerContext) -> SolrFields:
    pcdm_resource = PCDMObjectResource(ctx.repo, ctx.resource.path)
    text_pages = get_text_pages(pcdm_resource)

    if any(page.tagged for page in text_pages):
        field_name = 'extracted_text__dps_txt'
    else:
        field_name = 'extracted_text__txt'

    return {
        field_name: ' '.join(str(p) for p in text_pages),
    }


def get_text_pages(resource: AggregationResource) -> list[PageText]:
    text_pages: list[PageText] = []
    for n, page_resource in enumerate(resource.get_sequence(PCDMObjectResource)):  # type: int, PCDMObjectResource
        page = get_text_page(page_resource, n)
        if page is not None:
            text_pages.append(page)
    return text_pages


def get_text_page(page_resource: PCDMFileBearingResource, page_index: int) -> PageText:
    """Try to get a `PageText` object representing the textual content of the given
    page resource.

    * If the page has an extracted text file (RDF type `pcdmuse:ExtractedText`), try
      to parse that file, and return the text content tagged with the word-level xywh
      bounding box coordinates. If the file is not a recognized format, raises
      a `solrizer.indexers.IndexerError`.
    * If the page has an HTML file (MIME type `text/html`), uses BeautifulSoup to
      strip out the markup and just returns the plain text.
    * If the page has a plain text file (MIME type `text/plain`), return the content
      of that file unaltered.
    """
    if ocr_file := page_resource.get_file(rdf_type=pcdmuse.ExtractedText):
        image_with_ocr = ImageWithOCR(
            ocr_file=ocr_file,
            image_file=page_resource.get_file(rdf_type=pcdmuse.PreservationMasterFile),
        )
        try:
            return PageText(
                text=' '.join(get_tagged_ocr_text(image_with_ocr.get_ocr_resource(), page_index)),
                page_index=page_index,
                tagged=True,
            )
        except ImageFileError as e:
            raise IndexerError(f'Problem with image file: {e}') from e
        except UnrecognizedOCRFormatError as e:
            raise IndexerError(f'Unsupported extracted text document: {ocr_file}') from e

    if html_file := page_resource.get_file(mime_type='text/html'):
        with html_file.open() as fh:
            return PageText(BeautifulSoup(b''.join(fh), features='lxml').get_text(), page_index=page_index)

    if text_file := page_resource.get_file(mime_type='text/plain'):
        with text_file.open() as fh:
            return PageText(fh.read().decode(), page_index=page_index)


def get_tagged_ocr_text(ocr_resource: OCRResource, page_index: int) -> Iterator[str]:
    """Returns an iterator of the captured words from the OCR resource,
    in the format `{words}|n={page_index}&xywh={x,y,w,h}`."""

    for word in ocr_resource.words():
        yield f'{word}|{urlencode({'n': page_index, 'xywh': word.xywh}, safe=',')}'

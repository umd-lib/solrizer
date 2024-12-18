"""
Indexer Name: **`extracted_text`**

Indexer implementation function: `extracted_text_fields()`

Prerequisites: None

Output fields:

| Field              | Python Type | Solr Type                                    |
|--------------------|-------------|----------------------------------------------|
| `content__dps_txt` | `str`       | tokenized text with delimited string payload |
"""

from dataclasses import dataclass
from typing import Iterator
from urllib.parse import urlencode

from PIL import Image
from bs4 import BeautifulSoup
from lxml import etree
from plastron.namespaces import pcdmuse
from plastron.repo.pcdm import PCDMObjectResource, PCDMFileBearingResource

from solrizer.indexers import IndexerContext, SolrFields, IndexerError
from solrizer.ocr.alto import ALTOResource


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
    text_pages: list[PageText] = []
    pcdm_resource = PCDMObjectResource(ctx.repo, ctx.resource.path)
    for n, page_resource in enumerate(pcdm_resource.get_sequence(PCDMObjectResource)):  # type: int, PCDMObjectResource
        text_pages.append(get_page_text(page_resource, n))

    if any(page.tagged for page in text_pages):
        field_name = 'extracted_text__dps_txt'
    else:
        field_name = 'extracted_text__txt'

    return {
        field_name: ' '.join(str(p) for p in text_pages if p is not None),
    }


def get_page_text(page_resource: PCDMFileBearingResource, page_index: int) -> PageText:
    """Try to get a `PageText` object representing the textual content of the given
    page resource.

    * If the page has an HTML file (MIME type `text/html`), uses BeautifulSoup to
      strip out the markup and just returns the plain text.
    * If the page has a plain text file (MIME type `text/plain`), return the content
      of that file unaltered.
    * If the page has an extracted text file (RDF type `pcdmuse:ExtractedText`), try
      to parse that file as ALTO XML, and return the text content tagged with the
      word-level xywh bounding box coordinates. If the file is not ALTO XML, raises
      a `solrizer.indexers.IndexerError`. If the file is ALTO XML, but there is no
      preservation master file (RDF type `pcdmuse:PreservationMasterFile`), raises
      a `solrizer.indexers.IndexerError`.
    """
    if html_file := page_resource.get_file(mime_type='text/html'):
        with html_file.open() as fh:
            # TODO: here is where we could try to detect hOCR, unless there is a more specific MIME type for it
            return PageText(BeautifulSoup(b''.join(fh), features='lxml').get_text(), page_index=page_index)

    if text_file := page_resource.get_file(mime_type='text/plain'):
        with text_file.open() as fh:
            return PageText(fh.read().decode(), page_index=page_index)

    if ocr_file := page_resource.get_file(rdf_type=pcdmuse.ExtractedText):
        with ocr_file.open() as fh:
            xmldoc = etree.parse(fh)

        root = xmldoc.getroot()
        if root.tag == '{http://www.loc.gov/standards/alto/ns-v2#}alto':
            preservation_file = page_resource.get_file(rdf_type=pcdmuse.PreservationMasterFile)
            if preservation_file is None:
                raise IndexerError(f'No preservation file for {page_resource}, cannot determine image resolution')

            with preservation_file.open() as fh:
                img = Image.open(fh)
                res = img.info['dpi']
            alto_file = ALTOResource(xmldoc, res)
            return PageText(' '.join(get_tagged_ocr_text(alto_file, page_index)), page_index=page_index, tagged=True)
        else:
            raise IndexerError(f'Unsupported extracted text document: {ocr_file}')


def get_tagged_ocr_text(alto_file: ALTOResource, page_index: int) -> Iterator[str]:
    """Returns an iterator of the captured strings from the ALTO resource,
    in the format `{string}|n={page_index}&xywh={x,y,w,h}`."""

    for string in alto_file.strings:
        params = {
            'n': page_index,
            'xywh': string.xywh,
        }
        yield f'{string.content}|{urlencode(params, safe=',')}'

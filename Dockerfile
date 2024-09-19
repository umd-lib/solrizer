FROM python:3.12.6-slim

EXPOSE 5000

ENV FLASK_DEBUG=0
ENV SOLRIZER_FCREPO_JWT_SECRET={get secret from kubernetes}
ENV SOLRIZER_FCREPO_ENDPOINT=https://fcrepo-test.lib.umd.edu/fcrepo/rest
ENV SOLRIZER_IIIF_IDENTIFIER_PREFIX=fcrepo:
ENV SOLRIZER_IIIF_MANIFESTS_URL_PATTERN=https://iiif-test.lib.umd.edu/manifests/{+id}/manifest.json
ENV SOLRIZER_IIIF_THUMBNAIL_URL_PATTERN=https://iiif-test.lib.umd.edu/images/iiif/2/{+id}/full/250,/0/default.jpg
ENV SOLRIZER_INDEXERS=content_model,discoverability,page_sequence,iiif_links,dates,facets

WORKDIR /opt/solrizer

RUN apt-get update && apt-get install -y git && apt-get clean
RUN pip install git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-utils \
 git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-client \
 git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-rdf \
 git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-models \
 git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-repo

COPY src pyproject.toml /opt/solrizer/
RUN pip install -e .

ENTRYPOINT [ "solrizer" ]

FROM python:3.12.6-slim

EXPOSE 5000

ENV FLASK_DEBUG=0
ENV SOLRIZER_IIIF_IDENTIFIER_PREFIX=fcrepo:
ENV SOLRIZER_INDEXERS={"__default__":["content_model","discoverability","page_sequence","iiif_links","dates","facets","extracted_text"],"Page":["content_model"]}

WORKDIR /opt/solrizer

RUN apt-get update && apt-get install -y git && apt-get clean
RUN pip install git+https://github.com/umd-lib/plastron.git@4.4.0-dev2#subdirectory=plastron-utils \
 git+https://github.com/umd-lib/plastron.git@4.4.0-dev2#subdirectory=plastron-client \
 git+https://github.com/umd-lib/plastron.git@4.4.0-dev2#subdirectory=plastron-rdf \
 git+https://github.com/umd-lib/plastron.git@4.4.0-dev2#subdirectory=plastron-models \
 git+https://github.com/umd-lib/plastron.git@4.4.0-dev2#subdirectory=plastron-repo

COPY src pyproject.toml /opt/solrizer/
RUN pip install -e .

ENTRYPOINT [ "solrizer" ]

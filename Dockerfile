FROM python:3.12.6-slim

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

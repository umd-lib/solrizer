FROM python:3.12.6-slim

EXPOSE 5000

ENV FLASK_DEBUG=0

WORKDIR /opt/solrizer

RUN apt-get update && apt-get install -y git && apt-get clean
RUN pip install git+https://github.com/umd-lib/plastron.git@4.4.0-dev3#subdirectory=plastron-utils \
 git+https://github.com/umd-lib/plastron.git@4.4.0-dev3#subdirectory=plastron-client \
 git+https://github.com/umd-lib/plastron.git@4.4.0-dev3#subdirectory=plastron-rdf \
 git+https://github.com/umd-lib/plastron.git@4.4.0-dev3#subdirectory=plastron-models \
 git+https://github.com/umd-lib/plastron.git@4.4.0-dev3#subdirectory=plastron-repo

COPY src pyproject.toml /opt/solrizer/
RUN pip install -e .

ENTRYPOINT [ "solrizer" ]

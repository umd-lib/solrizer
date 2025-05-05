FROM python:3.12.6-slim

EXPOSE 5000

ENV FLASK_DEBUG=0

WORKDIR /opt/solrizer

RUN apt-get update && apt-get install -y git && apt-get clean
RUN pip install \
    git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-utils \
    git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-client \
    git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-rdf \
    git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-models \
    git+https://github.com/umd-lib/plastron.git@release/4.4#subdirectory=plastron-repo

COPY src pyproject.toml /opt/solrizer/
RUN pip install -e .

# install patched version of python-edtf (see https://umd-dit.atlassian.net/browse/LIBFCREPO-1633)
pip install git+https://github.com/peichman-umd/python-edtf.git@68f0b36deee03a355e6bec9f255d718f0d9f032b

ENTRYPOINT [ "solrizer" ]

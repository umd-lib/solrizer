FROM python:3.12.6-slim

EXPOSE 5000

ENV FLASK_DEBUG=0

WORKDIR /opt/solrizer

RUN apt-get update && apt-get install -y git && apt-get clean

COPY src pyproject.toml /opt/solrizer/

# install patched version of python-edtf (see https://umd-dit.atlassian.net/browse/LIBFCREPO-1633)
RUN pip install git+https://github.com/peichman-umd/python-edtf.git@68f0b36deee03a355e6bec9f255d718f0d9f032b

RUN pip install -e ".[redis]"

VOLUME /var/cache/solrizer

ENTRYPOINT [ "solrizer" ]

FROM python:3.12.6-slim

WORKDIR /opt/solrizer

COPY src pyproject.toml /opt/solrizer/
RUN pip install -e .

ENTRYPOINT ["solrizer"]

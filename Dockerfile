FROM python:3.14.9-slim

EXPOSE 5000

ENV FLASK_DEBUG=0

WORKDIR /opt/solrizer

COPY src pyproject.toml /opt/solrizer/

RUN pip install -e ".[redis]"

VOLUME /var/cache/solrizer

ENTRYPOINT [ "solrizer" ]

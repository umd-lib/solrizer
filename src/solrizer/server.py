"""Solrizer web application served by the Waitress WSGI server.
It is registered as a script entry point with the name `solrizer`.

```
$ solrizer -h
Usage: solrizer [OPTIONS]

Options:
  --listen [ADDRESS]:PORT  Address and port to listen on. Default is
                           "0.0.0.0:5000".
  -V, --version            Show the version and exit.
  -h, --help               Show this message and exit.
```
"""

import logging

import click
from dotenv import load_dotenv
from waitress import serve

from solrizer import __version__
from solrizer.web import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    '--listen',
    default='0.0.0.0:5000',
    help='Address and port to listen on. Default is "0.0.0.0:5000".',
    metavar='[ADDRESS]:PORT',
)
@click.version_option(__version__, '--version', '-V')
@click.help_option('--help', '-h')
def run(listen):
    load_dotenv()
    server_identity = f'solrizer/{__version__}'
    logger.info(f'Starting {server_identity}')
    try:
        serve(
            app=create_app(),
            listen=listen,
            ident=server_identity,
        )
    except (OSError, RuntimeError) as e:
        logger.error(f'Exiting: {e}')
        raise SystemExit(1) from e

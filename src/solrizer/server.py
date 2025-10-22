"""Solrizer web application served by the
[Waitress](https://docs.pylonsproject.org/projects/waitress/) WSGI server.
It is registered as a script entry point with the name *solrizer*.

```
$ solrizer -h
Usage: solrizer [OPTIONS]

Options:
  --listen [ADDRESS]:PORT  Address and port to listen on. Default is
                           "0.0.0.0:5000".
  --threads NUMBER         Number of threads used to process requests. Default
                           is 8.
  -V, --version            Show the version and exit.
  -h, --help               Show this message and exit.
```

## Environment

Server configuration can also be set via environment variables.

| Env Variable           | Option      |
|------------------------|-------------|
| **`WAITRESS_LISTEN`**  | `--listen`  |
| **`WAITRESS_THREADS`** | `--threads` |

For application configuration, see the `solrizer.web` module.

---
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
    envvar='WAITRESS_LISTEN',
)
@click.option(
    '--threads',
    type=int,
    default=8,
    help='Number of threads used to process requests. Default is 8.',
    metavar='NUMBER',
    envvar='WAITRESS_THREADS',
)
@click.version_option(__version__, '--version', '-V')
@click.help_option('--help', '-h')
def run(listen: str, threads: int):
    load_dotenv()
    server_identity = f'solrizer/{__version__}'
    logger.info(f'Starting {server_identity}')
    try:
        if threads < 1:
            raise ValueError('Number of threads must be greater than 0')
        logger.info(f'Worker threads: {threads}')
        serve(
            app=create_app(),
            listen=listen,
            ident=server_identity,
            threads=threads,
        )
    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f'Exiting: {e}')
        raise SystemExit(1) from e

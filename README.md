# solrizer

RDF to Solr document converter microservice

## Development Setup

Requires Python 3.11

```zsh
git clone git@github.com:umd-lib/solrizer.git
cd solrizer
python -m venv --prompt "solrizer-py$(cat .python-version)" .venv
source .venv/bin/activate
pip install -e '.[test]'
```

### Running

Enabling debug mode provides live reloading when files are changed, as 
well as more detailed error pages.

```zsh
export FLASK_DEBUG=1
flask --app solrizer.web run
```

The application will be available at <http://localhost:5000>

### Tests

```zsh
pytest
```

With coverage information:

```zsh
pytest --cov src --cov-report term-missing tests
```

## License

See the [LICENSE](LICENSE.md) file for license rights and
limitations (Apache 2.0).

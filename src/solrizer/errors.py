import json
from typing import Any

from werkzeug import Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, InternalServerError


class ProblemDetailError(HTTPException):
    """Subclass of the Werkzeug `HTTPException` class that adds a `params`
    dictionary that `as_problem_detail()` uses to format the response details."""

    name: str
    """Used as the problem detail `title`."""
    description: str
    """Used as the problem detail `details`. The value is treated as a format
    string, and is filled in using the `params` dictionary."""

    def __init__(self, description=None, response=None, **params):
        super().__init__(description, response)
        self.params = params

    def as_problem_detail(self) -> dict[str, Any]:
        """Format the exception information as a dictionary with keys as
        specified in the [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)
        JSON Problem Details format.

        | RFC 9457 Key | Attribute |
        |--------------|-----------|
        | `"status"`   | `code`    |
        | `"title"`    | `name`    |
        | `"details"`  | `description`, formatted using the `params` dictionary |

        """
        return {
            'status': self.code,
            'title': self.name,
            'details': self.description.format(**self.params),
        }


class ResourceNotAvailable(ProblemDetailError, NotFound):
    """The resource requested is unavailable. This may be due to insufficient
    permissions to read the resource, or the resource simply not existing in
    the repository.

    The HTTP status is `404 Not Found`.

    Must provide a `uri` parameter to the constructor:

    ```python
    raise ResourceNotAvailable(uri='http://example.com/foo')
    ```
    """
    name = 'Resource is not available'
    description = 'Resource at "{uri}" is not available from the repository.'


class NoResourceRequested(ProblemDetailError, BadRequest):
    """No resource was requested.

    The HTTP status is `400 Bad Request`."""
    name = 'No resource requested'
    description = 'No resource URL or path was provided as part of this request.'


class UnknownCommand(ProblemDetailError, BadRequest):
    """Unknown value provided for the "command" query parameter.

    The HTTP status is `400 Bad Request`.

    Must provide a `value` parameter to the constructor:

    ```python
    raise BadQueryParameter(value='foo')
    ```
    """
    name = 'Unknown command'
    description = '"{value}" is not a recognized value for the "command" parameter.'


class BadIndexersParameter(ProblemDetailError, BadRequest):
    """Value provided for the "indexers" query parameter is invalid.

    Among the possibilities:

      * Empty value
      * Same indexer listed more than once
      * Unrecognized indexer

    The HTTP status is `400 Bad Request`.

    Must provide a `value` parameter to the constructor describing why the
    parameter is invalid.

    ```python
    raise BadIndexersParameter(value='foo')
    ```
    """
    name = 'Bad indexers parameter'
    description = '{value}'


class ConfigurationError(ProblemDetailError, InternalServerError):
    """The server is incorrectly configured.

    The HTTP status is `500 Internal Server Error`."""
    name = 'Configuration error'
    description = 'The server is incorrectly configured.'


def problem_detail_response(e: ProblemDetailError) -> Response:
    """Return a JSON Problem Detail ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457))
    for HTTP errors.

    This function is mainly intended to be registered as an error handler
    with a Flask app:

    ```python
    from flask import Flask
    from solrizer import problem_detail_response

    app = Flask(__name__)

    ...

    app.register_error_handler(ProblemDetailError, problem_detail_response)
    ```
    """
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps(e.as_problem_detail())
    response.content_type = 'application/problem+json'
    return response

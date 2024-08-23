import json
from typing import Any

from werkzeug import Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest


class ProblemDetailError(HTTPException):
    """Subclass of the Werkzeug `HTTPException` class that adds a `params`
    dictionary that `as_problem_detail` uses to format the response details."""
    def __init__(self, description=None, response=None, **params):
        super().__init__(description, response)
        self.params = params

    def as_problem_detail(self) -> dict[str, Any]:
        """Format the exception information as a dictionary with keys as
        specified in the RFC 9457 JSON Problem Details format."""
        return {
            'status': self.code,
            'title': self.name,
            'details': self.description.format(**self.params),
        }


class ResourceNotAvailable(ProblemDetailError, NotFound):
    name = 'Resource is not available'
    description = 'Resource at "{uri}" is not available from the repository.'


class NoResourceRequested(ProblemDetailError, BadRequest):
    name = 'No resource requested'
    description = 'No resource URL or path was provided as part of this request.'


def problem_detail_response(e: ProblemDetailError) -> Response:
    """Return a JSON Problem Detail (RFC 9457) for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps(e.as_problem_detail())
    response.content_type = 'application/problem+json'
    return response

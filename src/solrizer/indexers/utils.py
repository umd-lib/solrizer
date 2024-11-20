from datetime import datetime, timezone


def solr_datetime(dt_string: str) -> str:
    """Parse the given `dt_string` as an ISO 8601 timestamp, convert its
    timezone to UTC, and use the "Z" timezone marker that Solr expects
    instead of "+00:00".

    At minimum, the `dt_string` must be a fully qualified date
    in the format `YYYY-MM-DD`. Other abbreviated formats (such
    as `YYYY` or `YYYY-MM`) will result in a `ValueError`.

    If no time is specified, this function depends on the `datetime`
    library's behavior of defaulting the time to midnight (00:00:00).
    Partial times are padded out with zeroes.

    If there is no timezone information, the timezone is set to UTC."""
    dt = datetime.fromisoformat(dt_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat(sep='T').replace('+00:00', 'Z')

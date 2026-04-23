"""HTML entity escaping for all user-generated content sent with parse_mode=HTML."""
from html import escape as _escape


def esc(value) -> str:
    """Escape a value for safe use inside HTML parse_mode messages."""
    if value is None:
        return "—"
    return _escape(str(value))

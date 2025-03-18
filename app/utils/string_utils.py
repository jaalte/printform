import re
import codecs

def sanitize_string(s: str) -> str:
    """Removes special characters and replaces spaces with dashes."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', s).replace(' ', '-')

def unescape_string(s: str) -> str:
    """Unescapes a string using unicode escape."""
    return codecs.decode(s, 'unicode_escape')
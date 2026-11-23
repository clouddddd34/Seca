"""Local HTML status rendering; no network or shell execution."""
from html import escape


def render_status(label):
    return '<p>Status: ' + escape(label) + '</p>'

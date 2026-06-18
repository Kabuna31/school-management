"""
core/templatetags/core_extras.py

Custom template filters for the core app.

Usage in templates:
    {% load core_extras %}
    {{ existing_marks|dictkey:student.pk }}
"""
from django import template

register = template.Library()


@register.filter
def dictkey(d, key):
    """
    Look up a value in a dictionary by key inside a template.

    Example:
        {{ existing_marks|dictkey:student.pk }}

    Returns empty string if the dict is None or the key is missing,
    so score inputs render blank rather than throwing an error.
    """
    if not isinstance(d, dict):
        return ''
    return d.get(key, '')

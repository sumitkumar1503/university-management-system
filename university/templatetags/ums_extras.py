from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Look up a value in a dict by key inside templates."""
    if hasattr(mapping, "get"):
        return mapping.get(key)
    return None


@register.filter
def pct_bar(value):
    try:
        return min(100, max(0, float(value)))
    except (TypeError, ValueError):
        return 0

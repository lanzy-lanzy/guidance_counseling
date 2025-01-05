from django import template

register = template.Library()

@register.filter(name='ordinal')
def ordinal(value):
    """
    Converts an integer to its ordinal representation.
    1 -> 1st, 2 -> 2nd, 3 -> 3rd, etc.
    """
    try:
        value = int(value)
        if value % 100 in [11, 12, 13]:  # Special case for 11th, 12th, 13th
            return f"{value}th"
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(value % 10, 'th')
            return f"{value}{suffix}"
    except (ValueError, TypeError):
        return value

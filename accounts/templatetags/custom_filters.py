from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Filter to get a value from a dictionary by key
    Usage: {{ mydict|get_item:mykey }}
    """
    if dictionary is None:
        return None
    
    # Try integer conversion (for list indexing)
    try:
        key = int(key)
    except (ValueError, TypeError):
        pass
        
    try:
        return dictionary[key]
    except (KeyError, TypeError, IndexError):
        return None 
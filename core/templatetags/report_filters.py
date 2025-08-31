from django import template
import locale

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key."""
    if dictionary is None or not isinstance(dictionary, dict):
        return 0
    return dictionary.get(key, 0)

@register.filter
def format_number(value):
    """Format number with thousand separators."""
    if value is None:
        return "0"
    
    try:
        # Convert to float first to handle decimal values
        num = float(value)
        
        # Format with thousand separators
        if num == int(num):
            # Integer value
            return "{:,}".format(int(num))
        else:
            # Decimal value - show 2 decimal places
            return "{:,.2f}".format(num)
    except (ValueError, TypeError):
        return str(value)

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplies the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

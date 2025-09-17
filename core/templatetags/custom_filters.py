from django import template
import locale

register = template.Library()

@register.filter
def thousands_separator(value):
    try:
        return "{:,.2f}".format(float(value))
    except:
        return value

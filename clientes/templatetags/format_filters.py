import re
from django import template

register = template.Library()

@register.filter
def format_documento(value):
    """Formata CPF ou CNPJ automaticamente."""
    if not value:
        return ''
    value = re.sub(r'\D', '', str(value))
    if len(value) == 11:
        # Formata CPF: 000.000.000-00
        return f"{value[:3]}.{value[3:6]}.{value[6:9]}-{value[9:]}"
    elif len(value) == 14:
        # Formata CNPJ: 00.000.000/0000-00
        return f"{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}"
    return value

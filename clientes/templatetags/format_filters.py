import re
from django import template

register = template.Library()

@register.filter
def initials(value):
    """
    Retorna iniciais (2 letras) a partir de um nome.
    Ex.: "David Nóbrega" -> "DN", "Maria" -> "MA"
    """
    if not value:
        return ""

    parts = [p for p in re.split(r"\s+", str(value).strip()) if p]
    if not parts:
        return ""

    if len(parts) == 1:
        return (parts[0][:2]).upper()

    return (parts[0][:1] + parts[-1][:1]).upper()


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

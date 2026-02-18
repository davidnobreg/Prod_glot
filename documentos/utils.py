import re
from django.utils.html import strip_tags

def limpar_html_para_pdf(html):
    html = re.sub(r'<br\s*/?>', '\n', html)
    html = re.sub(r'</p>', '\n\n', html)
    html = re.sub(r'<p.*?>', '', html)
    html = re.sub(r'<li>', '• ', html)
    html = re.sub(r'</li>', '\n', html)

    # mantém negrito/itálico
    html = html.replace('<strong>', '<b>').replace('</strong>', '</b>')
    html = html.replace('<em>', '<i>').replace('</em>', '</i>')

    html = strip_tags(html, tags=['b', 'i'])
    return html.strip()

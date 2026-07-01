import base64
import os

from django.conf import settings


def render_pdf(html_str, css_path, base_url, cfg=None):
	"""Renderiza PDF usando o motor configurado em settings.PDF_ENGINE.
	Mantem assinatura compativel com o uso atual em gerar_pdf_documento."""
	engine = getattr(settings, "PDF_ENGINE", "weasyprint")
	if engine == "playwright":
		return _render_playwright(html_str, css_path, cfg)
	return _render_weasyprint(html_str, css_path, base_url)


def _render_weasyprint(html_str, css_path, base_url):
	from weasyprint import CSS, HTML

	stylesheets = [CSS(filename=css_path)] if css_path else []
	return HTML(string=html_str, base_url=base_url).write_pdf(stylesheets=stylesheets)


# Chromium ignora position:running()/content:element() -- os divs #cabecalho e
# #rodape do documento_base.html ficam visiveis no fluxo normal do body em vez
# de virar header/footer fixo. Escondidos aqui pq o header/footer real e
# montado a parte via header_template/footer_template (page.pdf()).
_HIDE_CABECALHO_RODAPE_CSS = "#cabecalho, #rodape { display: none !important; }"


def _render_playwright(html_str, css_path, cfg):
	from playwright.sync_api import sync_playwright

	css_content = ""
	if css_path and os.path.exists(css_path):
		with open(css_path, encoding="utf-8") as f:
			css_content = f.read()

	header_template, footer_template = _build_header_footer(cfg)
	margem_sup = cfg.margem_sup if cfg else 25
	margem_dir = cfg.margem_dir if cfg else 20
	margem_inf = cfg.margem_inf if cfg else 20
	margem_esq = cfg.margem_esq if cfg else 30

	with sync_playwright() as pw:
		browser = pw.chromium.launch()
		try:
			page = browser.new_page()
			page.set_content(html_str)
			if css_content:
				page.add_style_tag(content=css_content)
			page.add_style_tag(content=_HIDE_CABECALHO_RODAPE_CSS)
			pdf_bytes = page.pdf(
				format="A4",
				display_header_footer=True,
				header_template=header_template,
				footer_template=footer_template,
				margin={
					"top": f"{margem_sup}mm",
					"right": f"{margem_dir}mm",
					"bottom": f"{margem_inf}mm",
					"left": f"{margem_esq}mm",
				},
			)
		finally:
			browser.close()
	return pdf_bytes


def _build_header_footer(cfg):
	"""Monta header_template/footer_template a partir do ConfiguracaoDocumento.
	Chromium renderiza header/footer num contexto isolado que nao herda o
	<style> da pagina nem resolve path relativo de imagem (sem base_url,
	diferente do WeasyPrint) -- por isso o logo entra como data URI base64."""
	logo_html = ""
	if cfg and cfg.logo:
		try:
			with cfg.logo.open("rb") as f:
				logo_b64 = base64.b64encode(f.read()).decode("ascii")
			ext = cfg.logo.name.rsplit(".", 1)[-1].lower()
			mime = "image/png" if ext == "png" else "image/jpeg"
			largura = cfg.logo_largura or 120
			logo_html = (
				f'<img src="data:{mime};base64,{logo_b64}" '
				f'style="max-width:{largura}px;height:auto;display:block;margin:0 auto;">'
			)
		except Exception:
			logo_html = ""

	cabecalho_extra = cfg.cabecalho_html if cfg and cfg.cabecalho_html else ""
	rodape_extra = cfg.rodape_html if cfg and cfg.rodape_html else ""
	margem_dir = cfg.margem_dir if cfg else 20
	fonte = cfg.fonte_familia if cfg and cfg.fonte_familia else "Times New Roman"

	header_template = f"""
		<div style="width:100%;font-size:9pt;text-align:center;font-family:'{fonte}',serif;">
			{logo_html}
			{cabecalho_extra}
		</div>
	"""

	footer_template = f"""
		<div style="width:100%;font-size:8pt;color:#555;font-family:'{fonte}',serif;padding:0 {margem_dir}mm;">
			<div style="text-align:center;">{rodape_extra}</div>
			<div style="text-align:right;">
				Página <span class="pageNumber"></span> de <span class="totalPages"></span>
			</div>
		</div>
	"""
	return header_template, footer_template
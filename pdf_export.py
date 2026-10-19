import io
import re
import markdown
from xhtml2pdf import pisa

CSS = """
body { font-family: Helvetica; font-size: 11px; line-height: 1.4; }
h1 { font-size: 20px; }
h2 { font-size: 15px; margin-top: 14px; }
p { margin-bottom: 6px; }
"""

def md_to_pdf(md_text):
    md_text = re.sub(r"^(#+ .*)\n(?!\n)", r"\1\n\n", md_text, flags=re.M)
    md_text = re.sub(r"\n(?=\[\d+\] )", "\n\n", md_text)
    body = markdown.markdown(md_text, extensions=["tables"])
    html = (
        "<html><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>"
        + body + "</body></html>"
    )
    buf = io.BytesIO()
    pisa.CreatePDF(html, dest=buf)
    return buf.getvalue()

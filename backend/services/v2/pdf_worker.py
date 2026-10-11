"""Child process: deterministic A4 print, no provider, scripts or external requests."""
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

PRINT_STYLE = """
@page { size: A4; margin: 14mm 12mm; }
@media print {
  body { max-width: none; padding: 0; margin: 0; font: 10pt/1.55 'Microsoft YaHei','Noto Sans CJK SC',sans-serif; }
  h1 { font-size: 20pt; } h2 { font-size: 14pt; break-after: avoid; }
  section { margin: 7mm 0; break-inside: auto; }
  figure { margin: 5mm 0; break-inside: avoid; }
  svg { width: 100%; height: auto; max-height: 80mm; }
  table { table-layout: fixed; width: 100%; font-size: 8pt; }
  th,td { overflow-wrap: anywhere; word-break: break-word; padding: 1.8mm; }
  thead { display: table-header-group; } tr { break-inside: avoid; }
  .table-wrap { overflow: visible; } nav { display: none; }
  figcaption { font-size: 8pt; } details { display: block; }
  * { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
}
"""


def main():
    output, executable = Path(sys.argv[1]), sys.argv[2]
    html = sys.stdin.buffer.read().decode("utf-8")
    # Expanding existing metric definitions changes presentation only, not content.
    html = html.replace("<details>", "<details open>")
    html = html.replace("</head>", "<style>" + PRINT_STYLE + "</style></head>", 1)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True,
            args=["--disable-background-networking", "--disable-component-update"])
        try:
            context = browser.new_context(java_script_enabled=False, service_workers="block", offline=True)
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(html, wait_until="load", timeout=15000)
            page.emulate_media(media="print")
            page.pdf(path=str(output), format="A4", prefer_css_page_size=True, print_background=True,
                     tagged=True)
        finally:
            browser.close()


if __name__ == "__main__":
    main()

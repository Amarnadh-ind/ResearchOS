"""
Standalone PDF render worker — runs Playwright in its own process.
Called via subprocess from PDFGenerator to avoid Windows asyncio
subprocess NotImplementedError.

Usage:
  Render PDF:     python _pdf_worker.py render <html_path> <pdf_path>
  Count pages:    python _pdf_worker.py count <pdf_path>
  Render+count:   python _pdf_worker.py render_count <html_path> <pdf_path>
"""

import json
import sys


def render(html_path: str, pdf_path: str) -> None:
    import os

    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
        except Exception as e:
            raise RuntimeError(f"Failed to launch Chromium: {e}") from e

        context = browser.new_context(
            viewport={"width": 816, "height": 1056},
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = context.new_page()

        try:
            page.goto(
                f"file:///{html_path.replace(os.sep, '/')}",
                wait_until="networkidle",
                timeout=30000,
            )
        except PlaywrightTimeout:
            page.goto(
                f"file:///{html_path.replace(os.sep, '/')}",
                wait_until="domcontentloaded",
                timeout=15000,
            )

        try:
            page.wait_for_function(
                "typeof renderMathInElement === 'function'",
                timeout=5000,
            )
            page.evaluate("""() => {
                return new Promise((resolve) => {
                    if (document.querySelector('.katex')) {
                        resolve(true);
                        return;
                    }
                    const observer = new MutationObserver(() => {
                        if (document.querySelector('.katex')) {
                            observer.disconnect();
                            resolve(true);
                        }
                    });
                    observer.observe(document.body, { childList: true, subtree: true });
                    setTimeout(() => { observer.disconnect(); resolve(false); }, 4000);
                });
            }""")
        except Exception:
            pass

        page.pdf(
            path=pdf_path,
            format="Letter",
            print_background=True,
            display_header_footer=True,
            header_template='<div style="width:100%;text-align:center;font-size:8pt;color:#888;font-family:Times New Roman,serif;padding-top:4pt;"></div>',
            footer_template='<div style="width:100%;text-align:center;font-size:8pt;color:#888;font-family:Times New Roman,serif;padding-bottom:4pt;"><span class="pageNumber"></span></div>',
            margin={
                "top": "0.75in",
                "bottom": "1.0in",
                "left": "0.625in",
                "right": "0.625in",
            },
        )
        browser.close()


def count_pages(pdf_path: str) -> int:
    """Count pages in a PDF file using binary parsing (no external deps)."""
    try:
        with open(pdf_path, "rb") as f:
            data = f.read()

        if not data:
            return 0

        import re
        pages = re.findall(rb'/Type\s*/Page[^s]', data)
        if pages:
            return len(pages)

        count_match = re.search(rb'/Count\s+(\d+)', data)
        if count_match:
            return int(count_match.group(1))

        size_kb = len(data) / 1024
        estimated = max(1, int(size_kb / 50))
        return estimated

    except Exception:
        return 0


def render_and_count(html_path: str, pdf_path: str) -> dict:
    """Render PDF and return page count."""
    render(html_path, pdf_path)
    pages = count_pages(pdf_path)
    return {"pdf_path": pdf_path, "page_count": pages}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python _pdf_worker.py <command> <args...>", file=sys.stderr)
        print("Commands: render <html> <pdf>, count <pdf>, render_count <html> <pdf>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "render":
        if len(sys.argv) != 4:
            print("Usage: python _pdf_worker.py render <html_path> <pdf_path>", file=sys.stderr)
            sys.exit(1)
        render(sys.argv[2], sys.argv[3])
        print(json.dumps({"status": "ok", "command": "render"}))

    elif command == "count":
        if len(sys.argv) != 3:
            print("Usage: python _pdf_worker.py count <pdf_path>", file=sys.stderr)
            sys.exit(1)
        pages = count_pages(sys.argv[2])
        print(json.dumps({"status": "ok", "command": "count", "page_count": pages}))

    elif command == "render_count":
        if len(sys.argv) != 4:
            print("Usage: python _pdf_worker.py render_count <html_path> <pdf_path>", file=sys.stderr)
            sys.exit(1)
        result = render_and_count(sys.argv[2], sys.argv[3])
        print(json.dumps({"status": "ok", "command": "render_count", **result}))

    else:
        if len(sys.argv) == 3:
            render(sys.argv[1], sys.argv[2])
            print(json.dumps({"status": "ok", "command": "render"}))
        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)

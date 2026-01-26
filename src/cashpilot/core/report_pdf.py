"""Utilities for rendering report PDFs using Playwright."""

from __future__ import annotations

import os
from typing import Optional

from playwright.async_api import async_playwright


async def render_pdf_from_url(
    *,
    url: str,
    base_url: str,
    session_cookie: Optional[str],
    wait_selector: str = "#reportContent:not(.hidden)",
    wait_for_flag: str = (
        "window.reportReady === true && window.reportChartsReady === true && "
        "document.getElementById('loadingState')?.classList.contains('hidden') && "
        "Array.from(document.querySelectorAll('#reportContent canvas')).every("
        "c => c.dataset.rendered === 'true' && c.width > 0 && c.height > 0)"
    ),
    footer_template: Optional[str] = None,
    locale: Optional[str] = None,
) -> bytes:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(locale=locale or "en-US")
        if session_cookie:
            await context.add_cookies(
                [
                    {
                        "name": "session",
                        "value": session_cookie,
                        "url": base_url,
                    }
                ]
            )

        page = await context.new_page()
        if locale:
            await page.set_extra_http_headers({"Accept-Language": locale})
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_selector(wait_selector, timeout=60_000)
        await page.wait_for_function(wait_for_flag, timeout=60_000)
        await page.wait_for_timeout(500)
        await page.emulate_media(media="print")

        footer_html = footer_template or (
            '<div style="font-size:10px; width:100%; text-align:right; padding-right:12mm;">'
            'Page <span class="pageNumber"></span> of <span class="totalPages"></span>'
            "</div>"
        )

        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=footer_html,
            margin={"top": "18mm", "bottom": "18mm", "left": "18mm", "right": "18mm"},
        )
        await context.close()
        await browser.close()
        return pdf_bytes


def get_internal_base_url(fallback: str) -> str:
    return os.getenv("INTERNAL_BASE_URL", fallback).rstrip("/")

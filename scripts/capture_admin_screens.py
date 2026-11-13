#!/usr/bin/env python3
"""Снимки живой панели диспетчера для отчёта ПМ.05.

Ожидает запущенный сайт (по умолчанию http://127.0.0.1:5000) и Google Chrome.
Учебный вход: admin / Admin123!
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images" / "report"


def shot(page, name: str, full_page: bool = False) -> None:
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page, type="png")
    print(f"saved {path}")


def login(page, base: str, user: str, password: str) -> None:
    page.goto(f"{base}/login", wait_until="networkidle")
    page.fill("#login", user)
    page.fill("#password", password)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def capture(base: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--hide-scrollbars", "--disable-gpu", "--no-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            locale="ru-RU",
        )
        page = context.new_page()
        page.set_default_timeout(20000)

        page.goto(f"{base}/", wait_until="networkidle")
        shot(page, "01-home")

        page.goto(f"{base}/login", wait_until="networkidle")
        shot(page, "02-login")

        login(page, base, "admin", "Admin123!")
        page.goto(f"{base}/admin", wait_until="networkidle")
        shot(page, "03-admin-list", full_page=True)

        page.goto(f"{base}/admin?status=done", wait_until="networkidle")
        shot(page, "04-admin-filter", full_page=True)

        page.goto(f"{base}/admin?page=2", wait_until="networkidle")
        shot(page, "05-admin-page2", full_page=True)

        page.goto(f"{base}/admin/requests/new", wait_until="networkidle")
        shot(page, "06-request-new", full_page=True)

        page.goto(f"{base}/admin/requests/1/edit", wait_until="networkidle")
        shot(page, "07-request-edit", full_page=True)

        page.goto(f"{base}/admin/requests/1/delete", wait_until="networkidle")
        shot(page, "08-request-delete")

        page.goto(f"{base}/admin/catalogs", wait_until="networkidle")
        shot(page, "09-catalogs", full_page=True)

        page.goto(f"{base}/admin/journal", wait_until="networkidle")
        shot(page, "10-journal", full_page=True)

        page.goto(f"{base}/admin/requests/999/edit", wait_until="networkidle")
        shot(page, "11-error-404")

        page.locator("form[action*='logout'] button").click()
        page.wait_for_load_state("networkidle")
        login(page, base, "demo", "Demo123!")
        page.goto(f"{base}/admin", wait_until="networkidle")
        shot(page, "12-error-403")

        browser.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    try:
        capture(args.base.rstrip("/"))
    except Exception as exc:  # noqa: BLE001 — скрипт одноразовый, ошибка на экран
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

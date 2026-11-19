import asyncio

import fastapi
import uvicorn
import pydantic
import requests
import PIL
import psutil
import yaml
import jinja2
import yt_dlp
import youtube_transcript_api
import pyautogui
import pygetwindow
import pywinauto
import mss
import keyboard
import webview
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content("<h1>MYRA offline browser test</h1>")
        assert await page.locator("h1").inner_text() == "MYRA offline browser test"
        await browser.close()
    print("MYRA_OFFLINE_CORE_AND_CHROMIUM_OK")


if __name__ == "__main__":
    asyncio.run(main())

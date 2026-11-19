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
import numpy
import cv2
import onnxruntime
import torch
import torchvision
import ultralytics
from rapidocr_onnxruntime import RapidOCR


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content("<h1>MYRA offline browser test</h1>")
        assert await page.locator("h1").inner_text() == "MYRA offline browser test"
        await browser.close()
    assert torch.__version__.startswith("2.14.1")
    assert torch.version.cuda is None, "The default bundled PyTorch build must be CPU-only and hardware-neutral."
    assert cv2.__version__
    assert onnxruntime.get_available_providers()
    print(f"MYRA_OFFLINE_CORE_VISION_AND_CHROMIUM_OK torch={torch.__version__} opencv={cv2.__version__} onnxruntime={onnxruntime.__version__}")


if __name__ == "__main__":
    asyncio.run(main())

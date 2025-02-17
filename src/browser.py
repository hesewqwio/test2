import contextlib
import locale
import logging
import os
import random
from pathlib import Path
from time import sleep
from typing import Type, Union
from types import TracebackType

import ipapi
import pycountry
from ipapi.exceptions import RateLimited
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver

from src.utils import CONFIG, getBrowserConfig, getProjectRoot, saveBrowserConfig

class Browser:
    """WebDriver wrapper class."""

    webdriver: Union[webdriver.Chrome, None]

    def __init__(self, mobile: bool) -> None:
        logging.debug("in __init__")
        self.mobile = mobile
        self.browserType = "mobile" if mobile else "desktop"
        self.headless = not CONFIG.browser.visible
        self.localeLang, self.localeGeo = self.getLanguageCountry()
        self.userDataDir = self.setupProfiles()
        self.browserConfig = getBrowserConfig(self.userDataDir)
        self.webdriver = self.browserSetup()
        logging.debug("out __init__")

    def __enter__(self):
        logging.debug("in __enter__")
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        logging.debug(
            f"in __exit__ exc_type={exc_type} exc_value={exc_value} traceback={traceback}"
        )
        self.webdriver.close()
        self.webdriver.quit()

    def browserSetup(self) -> webdriver.Chrome:
        options = ChromeOptions()
        options.headless = self.headless
        options.add_argument(f"--lang={self.localeLang}")
        options.add_argument("--log-level=3")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-certificate-errors-spki-list")
        options.add_argument("--ignore-ssl-errors")
        if os.environ.get("DOCKER"):
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-features=Translate")
        options.add_argument("--disable-features=PrivacySandboxSettings4")
        options.add_argument("--disable-http2")
        options.add_argument("--disable-search-engine-choice-screen")
        options.page_load_strategy = "eager"

        driver = webdriver.Chrome(options=options)

        if self.browserConfig.get("sizes"):
            deviceHeight = self.browserConfig["sizes"]["height"]
            deviceWidth = self.browserConfig["sizes"]["width"]
        else:
            if self.mobile:
                deviceHeight = random.randint(568, 1024)
                deviceWidth = random.randint(320, min(576, int(deviceHeight * 0.7)))
            else:
                deviceWidth = random.randint(1024, 2560)
                deviceHeight = random.randint(768, min(1440, int(deviceWidth * 0.8)))
            self.browserConfig["sizes"] = {
                "height": deviceHeight,
                "width": deviceWidth,
            }
            saveBrowserConfig(self.userDataDir, self.browserConfig)

        if self.mobile:
            screenHeight = deviceHeight + 146
            screenWidth = deviceWidth
        else:
            screenWidth = deviceWidth + 55
            screenHeight = deviceHeight + 151

        logging.info(f"Screen size: {screenWidth}x{screenHeight}")
        logging.info(f"Device size: {deviceWidth}x{deviceHeight}")

        if self.mobile:
            driver.execute_cdp_cmd(
                "Emulation.setTouchEmulationEnabled",
                {
                    "enabled": True,
                },
            )

        driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": deviceWidth,
                "height": deviceHeight,
                "deviceScaleFactor": 0,
                "mobile": self.mobile,
                "screenWidth": screenWidth,
                "screenHeight": screenHeight,
                "positionX": 0,
                "positionY": 0,
                "viewport": {
                    "x": 0,
                    "y": 0,
                    "width": deviceWidth,
                    "height": deviceHeight,
                    "scale": 1,
                },
            },
        )

        return driver

    def setupProfiles(self) -> Path:
        sessionsDir = getProjectRoot() / "sessions"
        sessionid = f"{self.browserType}"
        sessionsDir = sessionsDir / sessionid
        sessionsDir.mkdir(parents=True, exist_ok=True)
        return sessionsDir

    @staticmethod
    def getLanguageCountry() -> tuple[str, str]:
        country = CONFIG.browser.geolocation
        language = CONFIG.browser.language

        if not language or not country:
            currentLocale = locale.getlocale()
            if not language:
                with contextlib.suppress(ValueError):
                    language = pycountry.languages.get(
                        alpha_2=currentLocale[0].split("_")[0]
                    ).alpha_2
            if not country:
                with contextlib.suppress(ValueError):
                    country = pycountry.countries.get(
                        alpha_2=currentLocale[0].split("_")[1]
                    ).alpha_2

        if not language or not country:
            try:
                ipapiLocation = ipapi.location()
                if not language:
                    language = ipapiLocation["languages"].split(",")[0].split("-")[0]
                if not country:
                    country = ipapiLocation["country"]
            except RateLimited:
                logging.warning(exc_info=True)

        if not language:
            language = "en"
            logging.warning(
                f"Not able to figure language returning default: {language}"
            )

        if not country:
            country = "US"
            logging.warning(f"Not able to figure country returning default: {country}")

        return language, country

    @staticmethod
    def getChromeVersion() -> str:
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        driver = WebDriver(options=chrome_options)
        version = driver.capabilities["browserVersion"]

        driver.close()
        driver.quit()
        return version

    def visitURL(self, url: str, duration: int) -> None:
        self.webdriver.get(url)
        logging.info(f"Visited {url} for {duration} minutes.")
        sleep(duration * 60)

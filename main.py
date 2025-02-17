import logging
import logging.config
import logging.handlers as handlers
import sys
import traceback
from datetime import datetime
from selenium import webdriver

from src import Browser, Searches
from src.utils import CONFIG, sendNotification, getProjectRoot
from src.userAgentGenerator import get_user_agent  # Import the user agent generator

def setupLogging():
    _format = CONFIG['logging']['format']
    _level = CONFIG['logging']['level']
    terminalHandler = logging.StreamHandler(sys.stdout)
    terminalHandler.setFormatter(logging.Formatter(_format))

    logs_directory = getProjectRoot() / "logs"
    logs_directory.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": True,
        }
    )
    logging.basicConfig(
        level=logging.getLevelName(_level.upper()),
        format=_format,
        handlers=[
            handlers.TimedRotatingFileHandler(
                logs_directory / "activity.log",
                when="midnight",
                interval=1,
                backupCount=2,
                encoding="utf-8",
            ),
            terminalHandler,
        ],
    )

def perform_searches(mobile):
    options = webdriver.ChromeOptions()
    device_type = "mobile" if mobile else "desktop"
    user_agent = get_user_agent(device_type)  # Get user agent from userAgentGenerator.py
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--headless')
    
    with Browser(mobile=mobile, options=options) as browser:
        searches = Searches(browser=browser)
        searches.performSearch(CONFIG['url'], CONFIG['duration'])

def main():
    setupLogging()

    search_type = CONFIG['search']['type']

    try:
        if search_type in ("desktop", "both"):
            logging.info("Performing desktop searches...")
            perform_searches(mobile=False)  # Perform desktop searches

        if search_type in ("mobile", "both"):
            logging.info("Performing mobile searches...")
            perform_searches(mobile=True)  # Perform mobile searches

    except Exception as e:
        logging.exception("")
        sendNotification("⚠️ Error occurred, please check the log", traceback.format_exc(), e)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception("")
        sendNotification("⚠️ Error occurred, please check the log", traceback.format_exc(), e)
        exit(1)

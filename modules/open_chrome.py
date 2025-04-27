import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from config import *

# Suppress ChromeDriver and Selenium logs
os.environ['WDM_LOG_LEVEL'] = '0'
logging.getLogger('selenium').setLevel(logging.CRITICAL)
from selenium.webdriver.remote.remote_connection import LOGGER
LOGGER.setLevel(logging.CRITICAL)

# 1. Point this at your Chromedriver executable
CHROMEDRIVER_PATH = "C:/Program Files/Google/Chrome/chromedriver-win64/chromedriver.exe"

# 2. Build Service & Options
service = Service(
    executable_path=CHROMEDRIVER_PATH,
    log_path=os.devnull             # send driver logs to null
)
options = Options()
options.add_experimental_option("detach", True)
# suppress console logs
options.add_experimental_option("excludeSwitches", ["enable-logging"])
options.add_argument("--log-level=3")

# 3. Launch browser
driver = webdriver.Chrome(service=service, options=options)
driver.maximize_window()

# 4. Helpers for your scripts
wait    = WebDriverWait(driver, 10)
actions = ActionChains(driver)

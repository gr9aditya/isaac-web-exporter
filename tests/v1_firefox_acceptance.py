"""Run the final static package in the installed Mozilla Firefox browser."""

import json
import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait


url = os.getenv("ACCEPT_URL", "http://127.0.0.1:8002/")
output = Path(os.getenv("ACCEPT_OUTPUT", "runs/v1/firefox-box"))
options = Options()
options.add_argument("-headless")
driver = webdriver.Firefox(options=options)
driver.set_window_size(1280, 800)
result = {"url": url, "browser": driver.capabilities.get("browserName"),
          "version": driver.capabilities.get("browserVersion")}
try:
    driver.get(url)
    WebDriverWait(driver, 40).until(lambda browser: browser.execute_script(
        "return window.isaacReplay?.getState().duration > 0"))
    state = lambda: driver.execute_script("return window.isaacReplay.getState()")
    result["initial"] = state()
    if result["initial"]["playing"] or result["initial"]["time"] != 0:
        raise AssertionError("Initial playback state is wrong")
    driver.find_element(By.ID, "start").click()
    WebDriverWait(driver, 10).until(lambda browser: state()["time"] > 0.15)
    driver.find_element(By.ID, "pause").click()
    result["paused"] = state()
    driver.execute_script("window.isaacReplay.seek(2.5)")
    result["seeked"] = state()
    driver.find_element(By.ID, "step-forward").click()
    result["stepped"] = state()
    if result["stepped"]["time"] <= result["seeked"]["time"]:
        raise AssertionError("Frame step failed")
    driver.find_element(By.ID, "restart").click()
    result["restart"] = state()
    if not result["restart"]["playing"] or result["restart"]["time"] > 0.2:
        raise AssertionError("Restart failed")
    driver.find_element(By.ID, "pause").click()
    driver.find_element(By.CSS_SELECTOR, '.object-row').click()
    result["selected"] = state()
    if result["selected"]["selectedId"] != "/World/FallingBox":
        raise AssertionError("Object selection failed")
    result["renderer"] = driver.execute_script("""
      const gl = document.querySelector('#canvas canvas').getContext('webgl2');
      const extension = gl.getExtension('WEBGL_debug_renderer_info');
      return extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unreported';
    """)
    driver.save_screenshot(str(output.with_suffix(".png")))
    result["status"] = "PASS"
except Exception as error:
    result["status"] = "FAIL"
    result["failure"] = repr(error)
    raise
finally:
    output.with_suffix(".json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    driver.quit()

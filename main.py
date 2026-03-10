import os
import threading
import time
import requests
import base64
import json
from pathlib import Path
from fastapi import FastAPI
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import uvicorn

app = FastAPI()
execution_logs = []

# ------------------- INICIALIZAR WEBDRIVER -------------------
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# Ajustar binarios para Railway/Docker
chrome_options.binary_location = "/usr/bin/google-chrome"
service = Service("/usr/local/bin/chromedriver")

driver = webdriver.Chrome(service=service, options=chrome_options)

def log(msg: str):
    execution_logs.append(msg)
    print(msg)

# ------------------- ENDPOINTS -------------------

@app.post("/navegar")
def navegar(url: str):
    driver.get(url)
    log(f"Navegado a {url}")
    return {"status": "ok", "url": url}

@app.get("/xpaths")
def get_xpaths():
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//button | //input | //textarea | //*[@contenteditable='true']")
            )
        )
    except:
        return {"xpaths": []}

    elementos = []
    for el in driver.find_elements(By.XPATH, "//button | //input | //textarea | //*[@contenteditable='true']"):
        if el.is_displayed():
            xp = build_xpath(el)
            if xp:
                desc = el.text.strip() if el.text else (
                    el.get_attribute("placeholder") or el.get_attribute("value") or
                    el.get_attribute("name") or el.get_attribute("id") or ""
                )
                elementos.append({"xpath": xp, "descripcion": desc, "tipo": el.tag_name.lower()})

    return {"elementos": elementos}

def build_xpath(el):
    return driver.execute_script(
        """function absoluteXPath(element){
            var comp, comps = [];
            var parent = null;
            var xpath = '';
            var getPos = function(element){
                var position = 1, curNode;
                for (curNode = element.previousSibling; curNode; curNode = curNode.previousSibling){
                    if (curNode.nodeName == element.nodeName){
                        ++position;
                    }
                }
                return position;
            };
            if (element instanceof Document){
                return '/';
            }
            for (; element && !(element instanceof Document); element = element.parentNode){
                comp = comps[comps.length] = {};
                comp.name = element.nodeName;
                comp.position = getPos(element);
            }
            for (var i = comps.length - 1; i >= 0; i--){
                comp = comps[i];
                xpath += '/' + comp.name.toLowerCase();
                if (comp.position != null){
                    xpath += '[' + comp.position + ']';
                }
            }
            return xpath;
        } return absoluteXPath(arguments[0]);""", el)

@app.get("/screenshots")
def screenshot():
    png = driver.get_screenshot_as_base64()
    log("Captura de pantalla tomada")
    return {"screenshot": png}

@app.post("/refrescar")
def refrescar():
    driver.refresh()
    log("Página refrescada")
    return {"status": "ok"}

@app.post("/clicar")
def clicar(xpath: str):
    elem = driver.find_element(By.XPATH, xpath)
    elem.click()
    log(f"Clic en {xpath}")
    return {"status": "ok"}

@app.post("/input")
def escribir(xpath: str, texto: str):
    elem = driver.find_element(By.XPATH, xpath)
    elem.clear()
    elem.send_keys(texto)
    log(f"Texto '{texto}' introducido en {xpath}")
    return {"status": "ok"}

# ------------------- KEEP ALIVE -------------------

def keep_alive():
    url = os.getenv("RAILWAY_PUBLIC_URL")
    if not url:
        log("No se encontró RAILWAY_PUBLIC_URL, keep_alive desactivado")
        return
    while True:
        try:
            requests.get(url, timeout=10)
            log(f"Ping a {url} para mantener vivo el servicio")
        except Exception as e:
            log(f"Error en keep_alive: {e}")
        time.sleep(60)

threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
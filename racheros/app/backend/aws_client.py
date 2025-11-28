import requests
import os

USUARIOS_URL = os.environ.get("API_USUARIOS")
HABITOS_URL = os.environ.get("API_HABITOS")
PROGRESO_URL = os.environ.get("API_PROGRESO")

def call_lambda(url, payload):
    headers = {"Content-Type": "application/json"}
    res = requests.post(url, json=payload, headers=headers)
    return res.json()

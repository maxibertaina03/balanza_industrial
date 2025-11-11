# src/data_manager.py
import json
import os
from datetime import datetime

def load_config():
    if os.path.exists("balanza_config.json"):
        try:
            with open("balanza_config.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                history = data.get("current_history", [])
                expeditions = data.get("expeditions", [])
                last_product = data.get("last_product", "")
                
                # Asegurar campos nuevos
                for entry in history:
                    entry.setdefault('lote', '')
                    entry.setdefault('hormas', 0)
                    entry.setdefault('timestamp', "Sin fecha")
                for exp in expeditions:
                    for entry in exp.get('records', []):
                        entry.setdefault('lote', '')
                        entry.setdefault('hormas', 0)
                        entry.setdefault('timestamp', "Sin fecha")
                
                return history, expeditions, last_product
        except Exception as e:
            print(f"Error cargando config: {e}")
    return [], [], ""

def save_config(history, expeditions, last_product):
    data = {
        "current_history": history,
        "expeditions": expeditions,
        "last_product": last_product
    }
    try:
        with open("balanza_config.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error guardando: {e}")

def load_password():
    try:
        if os.path.exists("balanza_password.json"):
            with open("balanza_password.json", 'r') as f:
                return json.load(f).get("password", "admin123")
    except:
        pass
    return "admin123"

def save_password(password):
    try:
        with open("balanza_password.json", 'w') as f:
            json.dump({"password": password}, f)
        return True
    except:
        return False 
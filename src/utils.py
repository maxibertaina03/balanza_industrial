# src/utils.py
import json
import os
import time  # ← ESTO FALTABA

def hexdump(b):
    return ' '.join(f'{c:02X}' for c in b)

def read_realtime_data():
    try:
        if os.path.exists("balanza_realtime.json"):
            with open("balanza_realtime.json", 'r') as f:
                return json.load(f)
    except:
        pass
    return {"peso": 0.0, "reading": False, "last_update": 0, "status": "Detenido"}

def write_realtime_data(peso, reading, status="Leyendo"):
    try:
        data = {
            "peso": peso,
            "reading": reading,
            "last_update": time.time(),
            "status": status
        }
        with open("balanza_realtime.json", 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error escribiendo datos en tiempo real: {e}")
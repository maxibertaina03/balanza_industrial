# src/balance_reader.py
import serial
import re
import time
from .utils import hexdump

def parse_el05_corregido(data_bytes):
    try:
        data_str = data_bytes.decode('ascii', errors='ignore').strip()
        match = re.search(r'(\d+)', data_str)
        if match:
            raw_value = int(match.group(1))
            peso_val = raw_value / 1000.0
            return {
                "raw": data_bytes,
                "hex": hexdump(data_bytes),
                "peso_str": data_str,
                "peso_val": peso_val,
                "digits": match.group(1),
                "raw_value": raw_value
            }
    except Exception as e:
        print(f"ERROR parse: {e}")
    return None

def parse_cond(line_bytes):
    try:
        s = line_bytes.decode('ascii', errors='replace').strip('\r\n')
    except:
        s = ''
    if s and ord(s[0]) == 2:
        s = s[1:]
    sign = 1
    if s.startswith('-'):
        sign = -1
        s = s[1:]
    m = re.search(r'(-?\d+(\.\d+)?)', s)
    peso_val = None
    if m:
        try:
            peso_val = float(m.group(1)) * sign
        except:
            pass
    return {"peso_val": peso_val}

def continuous_reading(port, baud, formato):
    import random
    SIMULATE = True

    if SIMULATE:
        while True:
            from .utils import read_realtime_data, write_realtime_data
            realtime = read_realtime_data()
            if not realtime['reading']:
                time.sleep(0.5)
                continue
            peso = round(random.uniform(50.0, 500.0), 2)
            write_realtime_data(peso, True, "Leyendo (Simulación)")
            time.sleep(1.5)
    else:
        ser = None
        try:
            ser = serial.Serial(port=port, baudrate=baud, bytesize=8, parity='N', stopbits=1, timeout=1)
            time.sleep(2)
            from .utils import write_realtime_data
            write_realtime_data(0.0, True, f"Conectado a {port}")

            while True:
                from .utils import read_realtime_data, write_realtime_data
                realtime = read_realtime_data()
                if not realtime['reading']:
                    time.sleep(0.5)
                    continue

                try:
                    if formato == "el05":
                        raw = ser.read_until(b'\r')
                        parsed = parse_el05_corregido(raw)
                        if parsed and parsed['peso_val'] is not None:
                            write_realtime_data(parsed['peso_val'], True, f"Leyendo: {parsed['peso_val']:.2f} kg")
                        else:
                            write_realtime_data(0.0, True, "Esperando datos válidos")
                    elif formato == "cond":
                        raw = ser.read_until(b'\n')
                        parsed = parse_cond(raw)
                        if parsed and parsed['peso_val'] is not None:
                            write_realtime_data(parsed['peso_val'], True, f"Leyendo: {parsed['peso_val']:.2f} kg")
                        else:
                            write_realtime_data(0.0, True, "Dato inválido")
                    time.sleep(0.1)
                except Exception as e:
                    write_realtime_data(0.0, True, f"Error: {e}")
                    time.sleep(1)
        except Exception as e:
            from .utils import write_realtime_data
            write_realtime_data(0.0, False, f"Error: {e}")
        finally:
            if ser and ser.is_open:
                ser.close()
            from .utils import write_realtime_data
            write_realtime_data(0.0, False, "Desconectado")
            
            
            # ← NUEVO: Función para probar diferentes factores de escala
def probar_factor_escala():
    """Función para ayudar a determinar el factor de escala correcto"""
    test_data = b'M000010\r'  # Tu dato de ejemplo
    parsed = parse_el05_corregido(test_data)
    
    if parsed:
        raw_value = parsed['raw_value']
        print(f"\n=== PRUEBA FACTOR ESCALA ===")
        print(f"Dato RAW: {test_data}")
        print(f"Valor numérico: {raw_value}")
        print(f"División por 10: {raw_value / 10.0} kg")
        print(f"División por 100: {raw_value / 100.0} kg") 
        print(f"División por 1000: {raw_value / 1000.0} kg")
        print(f"División por 10000: {raw_value / 10000.0} kg")
        print("============================\n")


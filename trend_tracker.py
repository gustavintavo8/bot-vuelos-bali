import os
import sys
import io
import re
import csv
import requests
from datetime import datetime, timedelta
from amadeus import Client, ResponseError

# --- CONFIGURACIÓN DESDE VARIABLES DE ENTORNO ---
API_KEY = os.environ.get("AMADEUS_API_KEY")
API_SECRET = os.environ.get("AMADEUS_API_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ORIGENES = ["MAD", "BCN"]
DESTINO = "DPS"
ARCHIVO_HISTORIAL = "historial_extendido.csv"

# FECHAS Y FILTROS
FECHA_INICIO_BUSQUEDA = "2026-07-08" 
DIAS_A_ESCANEAR = 5   
DIAS_ESTANCIA = 10    
MAX_HORAS = 20.0      
PRECIO_MAXIMO = 1100
PRECIO_OBJETIVO = 800

def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try: requests.post(url, data=payload)
    except: pass

def analizar_vuelo(vuelo):
    itinerario = vuelo['itineraries'][0]
    segmentos = itinerario['segments']
    
    # 1. Tiempos
    salida = segmentos[0]['departure']['at']
    llegada = segmentos[-1]['arrival']['at']
    duracion_str = itinerario['duration']
    
    horas, minutos = 0, 0
    match_h = re.search(r'(\d+)H', duracion_str)
    match_m = re.search(r'(\d+)M', duracion_str)
    if match_h: horas = int(match_h.group(1))
    if match_m: minutos = int(match_m.group(1))
    duracion_total_minutos = (horas * 60) + minutos

    # 2. Detalles
    escalas = len(segmentos) - 1
    aerolinea_code = vuelo['validatingAirlineCodes'][0]
    numero_vuelo = f"{segmentos[0]['carrierCode']}{segmentos[0]['number']}"
    
    # 3. Rutas (Aeropuertos)
    aeropuertos_ruta = [seg['departure']['iataCode'] for seg in segmentos]
    aeropuertos_ruta.append(segmentos[-1]['arrival']['iataCode'])
    ruta_completa = ",".join(aeropuertos_ruta)
    
    if len(aeropuertos_ruta) > 2:
        aeropuertos_escala = ",".join(aeropuertos_ruta[1:-1])
    else:
        aeropuertos_escala = ""

    # 4. Precios
    precio_total = float(vuelo['price']['total'])
    precio_base = float(vuelo['price']['base'])
    impuestos = round(precio_total - precio_base, 2)
    
    try:
        clase = vuelo['travelerPricings'][0]['fareDetailsBySegment'][0]['cabin']
        asientos_quedan = vuelo['numberOfBookableSeats']
    except:
        clase = "N/A"
        asientos_quedan = "N/A"

    return {
        "salida_iso": salida, "llegada_iso": llegada,
        "duracion_min": duracion_total_minutos, "escalas": escalas,
        "aeropuertos_escala": aeropuertos_escala, "ruta_completa": ruta_completa,
        "aerolinea": aerolinea_code, "num_vuelo": numero_vuelo,
        "precio_total": precio_total, "precio_base": precio_base, "impuestos": impuestos,
        "clase": clase, "asientos": asientos_quedan
    }

def gestionar_historial(origen, datos_vuelo, fecha_salida):
    existe = os.path.isfile(ARCHIVO_HISTORIAL)
    precio_actual = datos_vuelo['precio_total']
    registros_previos = []

    if existe:
        with open(ARCHIVO_HISTORIAL, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['fecha_salida'] == fecha_salida and row['origen'] == origen:
                    try: registros_previos.append(float(row['precio_total']))
                    except: pass # Ignorar filas corruptas antiguas

    if not registros_previos: estado = "🆕 NUEVO"; diferencia = 0
    else:
        media = sum(registros_previos) / len(registros_previos)
        diferencia = precio_actual - media
        if diferencia < -5: estado = "📉 BAJADA"
        elif diferencia > 5: estado = "📈 SUBIDA"
        else: estado = "➖ IGUAL"

    # --- CORRECCIÓN IMPORTANTE AQUÍ ---
    # El orden debe coincidir EXACTAMENTE con tu CSV actual (Rutas al final)
    campos = [
        "fecha_consulta", "origen", "destino", "fecha_salida", 
        "hora_salida", "hora_llegada", "duracion_minutos", 
        "escalas", "aerolinea", "numero_vuelo", "clase", "asientos_disponibles",
        "precio_total", "precio_base", "impuestos", 
        "aeropuertos_escala", "ruta_completa"  # <--- MOVIDOS AL FINAL
    ]
    
    with open(ARCHIVO_HISTORIAL, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=campos)
        if not existe: writer.writeheader()
        
        fila = {
            "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "origen": origen, "destino": DESTINO, "fecha_salida": fecha_salida,
            "hora_salida": datos_vuelo['salida_iso'].split("T")[1],
            "hora_llegada": datos_vuelo['llegada_iso'].split("T")[1],
            "duracion_minutos": datos_vuelo['duracion_min'],
            "escalas": datos_vuelo['escalas'],
            "aerolinea": datos_vuelo['aerolinea'],
            "numero_vuelo": datos_vuelo['num_vuelo'],
            "clase": datos_vuelo['clase'],
            "asientos_disponibles": datos_vuelo['asientos'],
            "precio_total": datos_vuelo['precio_total'],
            "precio_base": datos_vuelo['precio_base'],
            "impuestos": datos_vuelo['impuestos'],
            "aeropuertos_escala": datos_vuelo['aeropuertos_escala'],
            "ruta_completa": datos_vuelo['ruta_completa']
        }
        writer.writerow(fila)

    return estado, diferencia

def main():
    if not API_KEY or not API_SECRET:
        print("❌ Error: Faltan claves API.")
        return

    amadeus = Client(client_id=API_KEY, client_secret=API_SECRET)
    print(f"📊 Buscando vuelos a {DESTINO}...")
    
    fecha_base = datetime.strptime(FECHA_INICIO_BUSQUEDA, "%Y-%m-%d")
    reporte = f"✈️ <b>REPORTE BALI</b>\n"
    novedades = False

    for origen in ORIGENES:
        for i in range(DIAS_A_ESCANEAR):
            fecha_ida = fecha_base + timedelta(days=i)
            fecha_vuelta = fecha_ida + timedelta(days=DIAS_ESTANCIA)
            str_ida = fecha_ida.strftime("%Y-%m-%d")
            str_vuelta = fecha_vuelta.strftime("%Y-%m-%d")

            try:
                res = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=origen, destinationLocationCode=DESTINO,
                    departureDate=str_ida, returnDate=str_vuelta,
                    adults=1, max=3, currencyCode='EUR'
                )

                if not res.data: continue
                
                # Buscar mejor opción
                mejor_vuelo = None
                for v in res.data:
                    dur_str = v['itineraries'][0]['duration']
                    h, m = 0, 0
                    if 'H' in dur_str: h = int(re.search(r'(\d+)H', dur_str).group(1))
                    if 'M' in dur_str: m = int(re.search(r'(\d+)M', dur_str).group(1))
                    dur = h + (m/60)
                    precio = float(v['price']['total'])
                    
                    if dur <= MAX_HORAS and precio <= PRECIO_MAXIMO:
                        mejor_vuelo = v
                        break
                
                if mejor_vuelo:
                    datos = analizar_vuelo(mejor_vuelo)
                    estado, dif = gestionar_historial(origen, datos, str_ida)
                    print(f"✅ {str_ida} ({origen}): {datos['precio_total']}€")

                    # Notificación
                    bajo_target = datos['precio_total'] < PRECIO_OBJETIVO
                    if estado in ["🆕 NUEVO", "📉 BAJADA"] or bajo_target:
                        novedades = True
                        icono = "🚨" if bajo_target else ("🟢" if estado == "📉 BAJADA" else "🔵")
                        dur_h = datos['duracion_min'] / 60
                        
                        reporte += f"\n{icono} <b>{origen} ({str_ida})</b>"
                        reporte += f"\n💰 {datos['precio_total']}€ ({dur_h:.1f}h)"
                        
                        fi = str_ida.replace("-", "")[2:]
                        fv = str_vuelta.replace("-", "")[2:]
                        link = f"https://www.skyscanner.es/transporte/vuelos/{origen}/{DESTINO}/{fi}/{fv}/"
                        reporte += f"\n<a href='{link}'>Ver oferta</a>\n"

            except Exception as e:
                print(f"Error {str_ida}: {e}")

    if novedades: enviar_telegram(reporte)

if __name__ == "__main__":
    main()
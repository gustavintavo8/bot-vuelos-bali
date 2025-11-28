import os
import sys
import io
import re
import csv
import requests # Necesitarás añadir esto al requirements.txt
from datetime import datetime, timedelta
from amadeus import Client, ResponseError

# --- CONFIGURACIÓN DESDE VARIABLES DE ENTORNO (SEGURIDAD) ---
API_KEY = os.environ.get("AMADEUS_API_KEY")
API_SECRET = os.environ.get("AMADEUS_API_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ORIGENES = ["MAD", "BCN"]
DESTINO = "DPS"
ARCHIVO_HISTORIAL = "historial_vuelos.csv"

# FECHAS Y FILTROS
FECHA_INICIO_BUSQUEDA = "2026-07-08" 
DIAS_A_ESCANEAR = 5   
DIAS_ESTANCIA = 15    
MAX_HORAS = 26.0      
PRECIO_MAXIMO = 1300

def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ No hay configuración de Telegram, saltando envío.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def gestionar_historial(fecha_salida, origen, precio_actual):
    existe = os.path.isfile(ARCHIVO_HISTORIAL)
    registros_previos = []

    if existe:
        with open(ARCHIVO_HISTORIAL, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['fecha_salida'] == fecha_salida and row['origen'] == origen:
                    registros_previos.append(float(row['precio']))

    if not registros_previos:
        estado = "🆕 NUEVO"
        media = precio_actual
        diferencia = 0
    else:
        media = sum(registros_previos) / len(registros_previos)
        diferencia = precio_actual - media
        if diferencia < -5: estado = "📉 BAJADA"
        elif diferencia > 5: estado = "📈 SUBIDA"
        else: estado = "➖ IGUAL"

    # Guardar nuevo dato
    with open(ARCHIVO_HISTORIAL, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not existe:
            writer.writerow(["fecha_consulta", "origen", "destino", "fecha_salida", "precio", "aerolinea"])
        hoy = datetime.now().strftime("%Y-%m-%d")
        writer.writerow([hoy, origen, DESTINO, fecha_salida, precio_actual, "N/A"])

    return estado, diferencia, media

def obtener_duracion(pt_string):
    h, m = 0, 0
    match_h = re.search(r'(\d+)H', pt_string)
    match_m = re.search(r'(\d+)M', pt_string)
    if match_h: h = int(match_h.group(1))
    if match_m: m = int(match_m.group(1))
    return h + (m / 60)

def main():
    if not API_KEY or not API_SECRET:
        print("❌ Error: Faltan las claves API en las variables de entorno.")
        return

    amadeus = Client(client_id=API_KEY, client_secret=API_SECRET)
    print(f"Analizando vuelos a {DESTINO}...")
    
    fecha_base = datetime.strptime(FECHA_INICIO_BUSQUEDA, "%Y-%m-%d")
    reporte_telegram = f"✈️ <b>REPORTE DIARIO BALI</b> ✈️\n"
    hubo_novedades = False

    for origen in ORIGENES:
        for i in range(DIAS_A_ESCANEAR):
            fecha_ida = fecha_base + timedelta(days=i)
            fecha_vuelta = fecha_ida + timedelta(days=DIAS_ESTANCIA)
            str_ida = fecha_ida.strftime("%Y-%m-%d")
            str_vuelta = fecha_vuelta.strftime("%Y-%m-%d")

            try:
                response = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=origen,
                    destinationLocationCode=DESTINO,
                    departureDate=str_ida,
                    returnDate=str_vuelta,
                    adults=1,
                    max=3,
                    currencyCode='EUR'
                )

                if not response.data: continue

                mejor_vuelo = None
                for vuelo in response.data:
                    dur = obtener_duracion(vuelo['itineraries'][0]['duration'])
                    prec = float(vuelo['price']['total'])
                    if dur <= MAX_HORAS and prec <= PRECIO_MAXIMO:
                        mejor_vuelo = (vuelo, dur, prec)
                        break
                
                if mejor_vuelo:
                    datos, duracion, precio = mejor_vuelo
                    estado, dif, media = gestionar_historial(str_ida, origen, precio)
                    
                    # Generar link Skyscanner (YYMMDD)
                    fi = str_ida.replace("-", "")[2:]
                    fv = str_vuelta.replace("-", "")[2:]
                    link = f"https://www.skyscanner.es/transporte/vuelos/{origen}/{DESTINO}/{fi}/{fv}/"

                    # Solo notificamos si es NUEVO o BAJA DE PRECIO para no saturar
                    if estado in ["🆕 NUEVO", "📉 BAJADA"]:
                        hubo_novedades = True
                        icono = "🟢" if estado == "📉 BAJADA" else "🔵"
                        reporte_telegram += f"\n{icono} <b>{origen} -> {DESTINO}</b> ({str_ida})\n"
                        reporte_telegram += f"   💰 <b>{precio}€</b> ({duracion:.1f}h)\n"
                        if estado == "📉 BAJADA":
                            reporte_telegram += f"   🔥 ¡{abs(dif):.0f}€ menos que la media!\n"
                        reporte_telegram += f"   <a href='{link}'>Ver en Skyscanner</a>\n"

            except Exception as e:
                print(f"Error buscando: {e}")

    if hubo_novedades:
        enviar_telegram(reporte_telegram)
    else:
        print("Sin novedades interesantes hoy.")

if __name__ == "__main__":
    main()
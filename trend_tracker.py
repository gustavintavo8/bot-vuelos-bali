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
# Usamos un nombre nuevo para no mezclar con el CSV antiguo que tiene menos columnas
ARCHIVO_HISTORIAL = "historial_extendido.csv"

# FECHAS Y FILTROS
FECHA_INICIO_BUSQUEDA = "2026-07-08" 
DIAS_A_ESCANEAR = 5   
DIAS_ESTANCIA = 10    
MAX_HORAS = 20.0      
PRECIO_MAXIMO = 1100
PRECIO_OBJETIVO = 750  # 🎯 Precio objetivo para alertas especiales

def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def analizar_vuelo(vuelo):
    """Extrae todos los detalles técnicos del objeto vuelo de Amadeus"""
    itinerario = vuelo['itineraries'][0]
    segmentos = itinerario['segments']
    
    # 1. Tiempos
    salida = segmentos[0]['departure']['at'] # Formato: 2026-07-08T10:00:00
    llegada = segmentos[-1]['arrival']['at']
    duracion_str = itinerario['duration']
    
    # Convertir duración a minutos (mejor para estadísticas)
    horas, minutos = 0, 0
    match_h = re.search(r'(\d+)H', duracion_str)
    match_m = re.search(r'(\d+)M', duracion_str)
    if match_h: horas = int(match_h.group(1))
    if match_m: minutos = int(match_m.group(1))
    duracion_total_minutos = (horas * 60) + minutos

    # 2. Detalles del viaje
    escalas = len(segmentos) - 1
    aerolinea_code = vuelo['validatingAirlineCodes'][0]
    numero_vuelo = f"{segmentos[0]['carrierCode']}{segmentos[0]['number']}"
    
    # 🗺️ NUEVO: Extraer aeropuertos de escala para el mapa
    aeropuertos_ruta = []
    for seg in segmentos:
        # Aeropuerto de salida de cada segmento
        aeropuertos_ruta.append(seg['departure']['iataCode'])
    # Añadir el último aeropuerto de llegada
    aeropuertos_ruta.append(segmentos[-1]['arrival']['iataCode'])
    
    # Convertir a string separado por comas: "MAD,DXB,DPS"
    ruta_completa = ",".join(aeropuertos_ruta)
    
    # Extraer solo las escalas (sin origen ni destino)
    if len(aeropuertos_ruta) > 2:
        aeropuertos_escala = ",".join(aeropuertos_ruta[1:-1])
    else:
        aeropuertos_escala = ""  # Vuelo directo
    
    # 3. Precios y Clase
    precio_total = float(vuelo['price']['total'])
    precio_base = float(vuelo['price']['base'])
    impuestos = round(precio_total - precio_base, 2)
    
    # Cabina (Economy, Business...) y asientos
    try:
        clase = vuelo['travelerPricings'][0]['fareDetailsBySegment'][0]['cabin']
        asientos_quedan = vuelo['numberOfBookableSeats']
    except:
        clase = "N/A"
        asientos_quedan = "N/A"

    return {
        "salida_iso": salida,
        "llegada_iso": llegada,
        "duracion_min": duracion_total_minutos,
        "escalas": escalas,
        "aeropuertos_escala": aeropuertos_escala,  # NUEVO
        "ruta_completa": ruta_completa,  # NUEVO
        "aerolinea": aerolinea_code,
        "num_vuelo": numero_vuelo,
        "precio_total": precio_total,
        "precio_base": precio_base,
        "impuestos": impuestos,
        "clase": clase,
        "asientos": asientos_quedan
    }

def gestionar_historial(origen, datos_vuelo, fecha_salida):
    existe = os.path.isfile(ARCHIVO_HISTORIAL)
    precio_actual = datos_vuelo['precio_total']
    registros_previos = []

    # Leemos historial para calcular tendencias
    if existe:
        with open(ARCHIVO_HISTORIAL, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['fecha_salida'] == fecha_salida and row['origen'] == origen:
                    registros_previos.append(float(row['precio_total']))

    # Lógica de tendencia
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

    # Guardar TODOS los datos en el CSV
    campos = [
        "fecha_consulta", "origen", "destino", "fecha_salida", 
        "hora_salida", "hora_llegada", "duracion_minutos", 
        "escalas", "aeropuertos_escala", "ruta_completa",  # NUEVO: campos de ruta
        "aerolinea", "numero_vuelo", "clase", "asientos_disponibles",
        "precio_total", "precio_base", "impuestos"
    ]
    
    with open(ARCHIVO_HISTORIAL, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=campos)
        if not existe:
            writer.writeheader()
        
        # Construimos la fila
        fila = {
            "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "origen": origen,
            "destino": DESTINO,
            "fecha_salida": fecha_salida,
            "hora_salida": datos_vuelo['salida_iso'].split("T")[1],
            "hora_llegada": datos_vuelo['llegada_iso'].split("T")[1],
            "duracion_minutos": datos_vuelo['duracion_min'],
            "escalas": datos_vuelo['escalas'],
            "aeropuertos_escala": datos_vuelo['aeropuertos_escala'],  # NUEVO
            "ruta_completa": datos_vuelo['ruta_completa'],  # NUEVO
            "aerolinea": datos_vuelo['aerolinea'],
            "numero_vuelo": datos_vuelo['num_vuelo'],
            "clase": datos_vuelo['clase'],
            "asientos_disponibles": datos_vuelo['asientos'],
            "precio_total": datos_vuelo['precio_total'],
            "precio_base": datos_vuelo['precio_base'],
            "impuestos": datos_vuelo['impuestos']
        }
        writer.writerow(fila)

    return estado, diferencia

def main():
    if not API_KEY or not API_SECRET:
        print("❌ Error: Faltan las claves API.")
        return

    amadeus = Client(client_id=API_KEY, client_secret=API_SECRET)
    print(f"📊 Recopilando BIG DATA de vuelos a {DESTINO}...")
    
    fecha_base = datetime.strptime(FECHA_INICIO_BUSQUEDA, "%Y-%m-%d")
    reporte_telegram = f"✈️ <b>REPORTE DETALLADO BALI</b> ✈️\n"
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

                # Buscamos el mejor vuelo según filtros
                mejor_vuelo_raw = None
                for vuelo in response.data:
                    # Análisis rápido solo para filtrar
                    dur_str = vuelo['itineraries'][0]['duration']
                    # (Reusamos la lógica de duración solo para el if)
                    h, m = 0, 0
                    if 'H' in dur_str: h = int(re.search(r'(\d+)H', dur_str).group(1))
                    if 'M' in dur_str: m = int(re.search(r'(\d+)M', dur_str).group(1))
                    dur_h = h + (m/60)
                    
                    prec = float(vuelo['price']['total'])
                    
                    if dur_h <= MAX_HORAS and prec <= PRECIO_MAXIMO:
                        mejor_vuelo_raw = vuelo
                        break
                
                if mejor_vuelo_raw:
                    # Extraemos TODOS los datos
                    datos = analizar_vuelo(mejor_vuelo_raw)
                    
                    # Guardamos en CSV y calculamos tendencia
                    estado, dif = gestionar_historial(origen, datos, str_ida)
                    
                    print(f"✅ {str_ida} ({origen}): {datos['precio_total']}€ | {datos['aerolinea']} | {datos['duracion_min']} min")

                    # 🎯 ALERTA ESPECIAL: Precio por debajo del objetivo
                    precio_bajo_objetivo = datos['precio_total'] < PRECIO_OBJETIVO
                    
                    # Notificación Telegram (Simplificada + Alerta Objetivo)
                    if estado in ["🆕 NUEVO", "📉 BAJADA"] or precio_bajo_objetivo:
                        hubo_novedades = True
                        
                        # Icono especial si está bajo el precio objetivo
                        if precio_bajo_objetivo:
                            icono = "🚨🔥"
                        elif estado == "📉 BAJADA":
                            icono = "🟢"
                        else:
                            icono = "🔵"
                        
                        dur_h = datos['duracion_min'] / 60
                        
                        reporte_telegram += f"\n{icono} <b>{origen} ({str_ida})</b>"
                        reporte_telegram += f"\n💰 <b>{datos['precio_total']}€</b> ({dur_h:.1f}h)"
                        reporte_telegram += f"\n🏢 {datos['aerolinea']} (Vuelo {datos['num_vuelo']})"
                        
                        # Mensaje especial para precio objetivo
                        if precio_bajo_objetivo:
                            reporte_telegram += f"\n🔥🔥🔥 ¡PRECIO BAJO OBJETIVO! 🚨🚨🚨"
                            reporte_telegram += f"\n💥 ¡COMPRA YA! Solo {datos['precio_total']}€"
                        elif estado == "📉 BAJADA":
                            reporte_telegram += f"\n🔥 ¡{abs(dif):.0f}€ menos!"
                        
                        # Link Skyscanner
                        fi = str_ida.replace("-", "")[2:]
                        fv = str_vuelta.replace("-", "")[2:]
                        link = f"https://www.skyscanner.es/transporte/vuelos/{origen}/{DESTINO}/{fi}/{fv}/"
                        reporte_telegram += f"\n<a href='{link}'>Ver oferta</a>\n"

            except Exception as e:
                print(f"Error procesando {str_ida}: {e}")

    if hubo_novedades:
        enviar_telegram(reporte_telegram)
    else:
        print("Sin novedades estadísticas hoy.")

if __name__ == "__main__":
    main()
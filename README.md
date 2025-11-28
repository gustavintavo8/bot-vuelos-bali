# ✈️ Bali Flight Tracker & Trend Bot

> Un bot automatizado en Python que rastrea precios de vuelos diarios, analiza tendencias históricas y notifica las mejores ofertas vía Telegram.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Amadeus API](https://img.shields.io/badge/API-Amadeus-orange.svg)
![GitHub Actions](https://img.shields.io/badge/Automation-GitHub%20Actions-green.svg)

## 📖 Descripción

Este proyecto es una herramienta de **inteligencia de precios de vuelos**. A diferencia de las alertas tradicionales, este script no solo busca el precio actual, sino que:

1.  **Construye un historial:** Guarda los precios día a día en un archivo `historial_vuelos.csv`.
2.  **Detecta tendencias:** Compara el precio de hoy con tu media histórica para decirte si el vuelo está bajando (📉) o subiendo (📈).
3.  **Filtra inteligentemente:** Solo busca vuelos con escalas cortas y duración optimizada (<26h).
4.  **Te avisa:** Si detecta una bajada de precio o una nueva oportunidad, envía un mensaje detallado a tu **Telegram** con un enlace directo de compra a Skyscanner.
5.  **100% Automatizado:** Se ejecuta cada mañana en la nube usando **GitHub Actions** (gratis).

## 🚀 Cómo funciona

El script `trend_tracker.py` realiza los siguientes pasos:
1.  Conecta con la **API de Amadeus** para obtener precios reales de aerolíneas.
2.  Busca vuelos desde **Madrid (MAD)** y **Barcelona (BCN)** hacia **Bali (DPS)** (configurable).
3.  Aplica filtros estrictos de duración y escalas.
4.  Guarda los resultados en `historial_vuelos.csv` y hace un *commit* automático al repositorio para no perder los datos.
5.  Si encuentra una oferta mejor que la media histórica, envía una alerta al bot de Telegram configurado.

## 🛠️ Instalación y Uso Local

Si quieres probarlo en tu ordenador antes de subirlo a la nube:

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/TU_USUARIO/bot-vuelos-bali.git](https://github.com/TU_USUARIO/bot-vuelos-bali.git)
    cd bot-vuelos-bali
    ```

2.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configurar Variables de Entorno:**
    El script necesita tus claves para funcionar. En Linux/Mac:
    ```bash
    export AMADEUS_API_KEY="tu_api_key"
    export AMADEUS_API_SECRET="tu_api_secret"
    # Opcionales para local (si no, solo imprime en consola)
    export TELEGRAM_TOKEN="tu_token"
    export TELEGRAM_CHAT_ID="tu_id"
    ```
    *(En Windows PowerShell usa `$env:AMADEUS_API_KEY="tu_clave"`)*

4.  **Ejecutar:**
    ```bash
    python trend_tracker.py
    ```

## ☁️ Automatización con GitHub Actions (Recomendado)

Para que el bot trabaje solo todos los días:

1.  Ve a la pestaña **Settings** de tu repositorio en GitHub.
2.  Entra en **Secrets and variables** > **Actions**.
3.  Crea los siguientes **New repository secrets**:

| Nombre del Secreto | Descripción |
|--------------------|-------------|
| `AMADEUS_API_KEY` | Tu API Key de [Amadeus Developers](https://developers.amadeus.com/). |
| `AMADEUS_API_SECRET` | Tu API Secret de Amadeus. |
| `TELEGRAM_TOKEN` | El token que te dio @BotFather en Telegram. |
| `TELEGRAM_CHAT_ID` | Tu ID numérico de usuario (obtenlo con @userinfobot). |

Una vez configurado, el flujo de trabajo (`.github/workflows/main.yml`) se ejecutará automáticamente **todos los días a las 08:00 UTC**.

## ⚙️ Personalización

Puedes editar las variables en la parte superior de `trend_tracker.py` para adaptar el viaje a tus necesidades:

```python
ORIGENES = ["MAD", "BCN"]      # Aeropuertos de salida
DESTINO = "DPS"                # Código IATA del destino (ej: JFK, TYO)
FECHA_INICIO_BUSQUEDA = "2026-07-08" # Fecha aproximada
DIAS_A_ESCANEAR = 5            # Cuántos días flexibles buscar
DIAS_ESTANCIA = 15             # Duración del viaje
MAX_HORAS = 26.0               # Duración máxima permitida
PRECIO_MAXIMO = 1300           # Presupuesto límite

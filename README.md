# ✈️ Bali Flight Tracker & Analytics Dashboard

> Un sistema completo de inteligencia de vuelos que rastrea precios diarios, detecta tendencias, notifica ofertas por Telegram y visualiza los datos en una web interactiva.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Amadeus API](https://img.shields.io/badge/API-Amadeus-orange.svg)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red.svg)
![GitHub Actions](https://img.shields.io/badge/Automation-GitHub%20Actions-green.svg)

## 📖 Descripción

Este proyecto va más allá de un simple rastreador. Es una suite completa de monitorización de precios para tu viaje a Bali:

1.  **Recopilación de Big Data:** El bot se ejecuta diariamente y extrae datos técnicos detallados (precio base vs impuestos, duración exacta en minutos, número de vuelo, modelo de avión, asientos disponibles...).
2.  **Base de Datos Histórica:** Guarda todo en `historial_extendido.csv`, creando un registro permanente de la evolución del mercado.
3.  **Alertas Inteligentes:** Si detecta una bajada real respecto a la media histórica, te envía un aviso inmediato a **Telegram**.
4.  **Web de Estadísticas (Dashboard):** Incluye una aplicación web (`app.py`) construida con **Streamlit** para visualizar gráficas de tendencias, mejores días para volar y comparativas de aerolíneas.
5.  **100% Automatizado:** GitHub Actions actualiza los datos cada mañana y Streamlit Cloud actualiza la web automáticamente.

## 🚀 Arquitectura del Proyecto

1.  **El Cerebro (`trend_tracker.py`):** Conecta con la API de Amadeus, filtra vuelos (duración < 26h, pocas escalas) y guarda los datos en CSV.
2.  **La Automatización (GitHub Actions):** Ejecuta el cerebro cada día a las 08:00 AM UTC y guarda los cambios en el repositorio.
3.  **La Visualización (`app.py`):** Lee el CSV generado y muestra un cuadro de mandos interactivo accesible desde cualquier navegador.

## 🛠️ Instalación y Uso Local

Si quieres ejecutarlo en tu ordenador:

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/TU_USUARIO/bot-vuelos-bali.git](https://github.com/TU_USUARIO/bot-vuelos-bali.git)
    cd bot-vuelos-bali
    ```

2.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configurar Variables de Entorno (Solo para el Rastreador):**
    ```bash
    export AMADEUS_API_KEY="tu_api_key"
    export AMADEUS_API_SECRET="tu_api_secret"
    export TELEGRAM_TOKEN="tu_token"
    export TELEGRAM_CHAT_ID="tu_id"
    ```
    *(En Windows PowerShell usa `$env:VARIABLE="valor"`)*

4.  **Ejecutar el Rastreador (Backend):**
    ```bash
    python trend_tracker.py
    ```

5.  **Ejecutar la Web de Estadísticas (Frontend):**
    ```bash
    python -m streamlit run app.py
    ```

## ☁️ Despliegue en la Nube (Gratis)

### Parte 1: El Bot de Datos (GitHub Actions)
Para que el bot recopile datos solo:
1.  Ve a **Settings** > **Secrets and variables** > **Actions** en tu repositorio.
2.  Añade tus claves: `AMADEUS_API_KEY`, `AMADEUS_API_SECRET`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.
3.  El bot se ejecutará automáticamente todos los días.

### Parte 2: La Web de Estadísticas (Streamlit Cloud)
Para publicar tu web y compartirla:
1.  Ve a [share.streamlit.io](https://share.streamlit.io/) y conecta con GitHub.
2.  Selecciona este repositorio.
3.  Archivo principal: `app.py`.
4.  ¡Dale a **Deploy**! Tu web se actualizará sola cada vez que el bot guarde nuevos datos.

## ⚙️ Personalización

Puedes editar las constantes en `trend_tracker.py` para cambiar el destino o filtros:

```python
ORIGENES = ["MAD", "BCN"]      # Aeropuertos de salida
DESTINO = "DPS"                # Destino
FECHA_INICIO_BUSQUEDA = "2026-07-08" 
DIAS_A_ESCANEAR = 5            # Ventana de flexibilidad
MAX_HORAS = 26.0               # Duración máxima
PRECIO_MAXIMO = 1300

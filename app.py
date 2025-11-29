import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Bali Flight Tracker", page_icon="✈️", layout="wide")

# Título y descripción
st.title("✈️ Monitor de Vuelos a Bali (DPS)")
st.markdown("Dashboard de inteligencia de precios. Datos extraídos vía API Amadeus.")

# --- CARGA DE DATOS ---
ARCHIVO_CSV = "historial_extendido.csv"

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_csv(ARCHIVO_CSV)
        # Convertir fechas a formato fecha real
        df['fecha_consulta'] = pd.to_datetime(df['fecha_consulta'])
        df['fecha_salida'] = pd.to_datetime(df['fecha_salida'])
        return df
    except FileNotFoundError:
        return None

df = cargar_datos()

if df is None:
    st.warning("⚠️ Todavía no hay datos. Ejecuta el script 'trend_tracker.py' para generar el historial.")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros")
origen_filtro = st.sidebar.multiselect(
    "Aeropuerto Origen", 
    options=df['origen'].unique(),
    default=df['origen'].unique()
)

# Filtrar el DataFrame
df_filtrado = df[df['origen'].isin(origen_filtro)]

# --- KPIs (Métricas Principales) ---
col1, col2, col3, col4 = st.columns(4)

precio_minimo = df_filtrado['precio_total'].min()
precio_medio = df_filtrado['precio_total'].mean()
mejor_vuelo = df_filtrado.loc[df_filtrado['precio_total'].idxmin()]
ultimo_dato = df_filtrado['fecha_consulta'].max()

col1.metric("💰 Mejor Precio Histórico", f"{precio_minimo:.0f}€")
col2.metric("📊 Precio Medio", f"{precio_medio:.0f}€")
col3.metric("✈️ Aerolínea Más Barata", mejor_vuelo['aerolinea'])
col4.metric("⏱️ Última Actualización", ultimo_dato.strftime("%d/%m %H:%M"))

st.divider()

# --- GRÁFICOS ---

# FILA 1
c1, c2 = st.columns(2)

with c1:
    st.subheader("📉 Evolución del Precio (Tendencia)")
    # Gráfico de línea: Eje X = Cuándo miraste el precio, Eje Y = Precio
    fig_evolucion = px.line(
        df_filtrado, 
        x='fecha_consulta', 
        y='precio_total', 
        color='origen',
        markers=True,
        title="¿Cómo cambian los precios día a día?"
    )
    st.plotly_chart(fig_evolucion, use_container_width=True)

with c2:
    st.subheader("🗓️ Precios por Fecha de Salida")
    # Gráfico de barras para ver qué día es más barato volar
    # Agrupamos por fecha de salida y cogemos el precio mínimo encontrado para ese día
    df_min_por_dia = df_filtrado.groupby('fecha_salida')['precio_total'].min().reset_index()
    
    fig_dias = px.bar(
        df_min_por_dia, 
        x='fecha_salida', 
        y='precio_total',
        text_auto='.0f',
        color='precio_total',
        color_continuous_scale='RdYlGn_r', # Rojo caro, Verde barato
        title="¿Qué día es más barato salir?"
    )
    st.plotly_chart(fig_dias, use_container_width=True)

# FILA 2
c3, c4 = st.columns(2)

with c3:
    st.subheader("⏳ Duración vs Precio")
    # Scatter plot: ¿Pagar más ahorra tiempo?
    fig_scatter = px.scatter(
        df_filtrado,
        x='duracion_minutos',
        y='precio_total',
        color='aerolinea',
        size='precio_total',
        hover_data=['numero_vuelo', 'escalas'],
        title="Relación Calidad/Precio (Abajo a la izq = Mejor)"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with c4:
    st.subheader("🏢 Aerolíneas Competitivas")
    # Boxplot para ver el rango de precios de cada aerolínea
    fig_box = px.box(
        df_filtrado,
        x='aerolinea',
        y='precio_total',
        color='aerolinea',
        title="Rango de precios por compañía"
    )
    st.plotly_chart(fig_box, use_container_width=True)

# --- TABLA DE DATOS DETALLADA ---
st.subheader("📋 Últimos Vuelos Encontrados")
st.dataframe(
    df_filtrado.sort_values(by="fecha_consulta", ascending=False).head(10),
    use_container_width=True
)
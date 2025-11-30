import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Bali Flight Tracker",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNCIÓN PARA CARGAR CSS EXTERNO ---
def cargar_css(nombre_archivo):
    try:
        with open(nombre_archivo) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"⚠️ No se encontró el archivo de estilos '{nombre_archivo}'.")

# Cargar estilos minimalistas
cargar_css("style.css")

# --- DICCIONARIO AEROLÍNEAS ---
AEROLINEAS_NOMBRES = {
    "QR": "Qatar Airways", "EK": "Emirates", "TK": "Turkish Airlines",
    "SQ": "Singapore Airlines", "CX": "Cathay Pacific", "EY": "Etihad",
    "KL": "KLM", "AF": "Air France", "SV": "Saudia", "GA": "Garuda",
    "MH": "Malaysia Airlines", "TG": "Thai Airways", "CI": "China Airlines",
    "MU": "China Eastern", "CZ": "China Southern"
}

def get_nombre_aerolinea(codigo):
    return AEROLINEAS_NOMBRES.get(codigo, codigo)

# --- CARGA DE DATOS ---
ARCHIVO_CSV = "historial_extendido.csv"

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_csv(ARCHIVO_CSV)
        df['fecha_consulta'] = pd.to_datetime(df['fecha_consulta'])
        df['fecha_salida'] = pd.to_datetime(df['fecha_salida'])
        df['nombre_aerolinea'] = df['aerolinea'].apply(get_nombre_aerolinea)
        df['duracion_horas'] = df['duracion_minutos'] / 60
        return df
    except FileNotFoundError:
        return None

# --- FUNCIÓN GRÁFICA: CALENDAR HEATMAP ---
def plot_calendar_heatmap(df):
    """Genera un mapa de calor tipo GitHub (Semana vs Día)"""
    # 1. Preparar datos
    df_cal = df.groupby('fecha_salida')['precio_total'].min().reset_index()
    
    # Extraer metadatos de fecha
    df_cal['semana'] = df_cal['fecha_salida'].dt.isocalendar().week
    df_cal['dia_semana'] = df_cal['fecha_salida'].dt.dayofweek # 0=Lun
    df_cal['texto_fecha'] = df_cal['fecha_salida'].dt.strftime('%d %b')
    df_cal['precio_texto'] = df_cal['precio_total'].apply(lambda x: f"{x:.0f}€")
    
    # 2. Pivotar para matriz (Y=Día, X=Semana)
    matriz_precios = df_cal.pivot(index='dia_semana', columns='semana', values='precio_total')
    matriz_hover = df_cal.pivot(index='dia_semana', columns='semana', values='texto_fecha')
    matriz_precio_str = df_cal.pivot(index='dia_semana', columns='semana', values='precio_texto')
    
    # 3. Combinar texto para el hover
    # (Plotly a veces es caprichoso con matrices de texto mixtas, simplificamos el hover)
    
    # 4. Crear Heatmap
    # Usamos escala de grises invertida: Negro = Barato, Blanco = Caro/Vacío
    fig = go.Figure(data=go.Heatmap(
        z=matriz_precios,
        x=matriz_precios.columns,
        y=['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
        text=matriz_precio_str, # Texto dentro del cuadro
        texttemplate="%{text}", 
        textfont={"size": 10, "family": "Inter"},
        hovertemplate="<b>%{text}</b><br>Semana %{x}<br>Precio: %{z:.0f}€<extra></extra>",
        colorscale='Greys', 
        reversescale=True, # Oscuro = Bajo Precio (Mejor)
        xgap=3, 
        ygap=3,
        showscale=False # Ocultar barra lateral para más limpieza
    ))
    
    fig.update_layout(
        title=dict(text="📅 Calendario de Oportunidades (Más oscuro = Más barato)", font=dict(size=14)),
        xaxis_title="Semana del Año",
        yaxis_title="",
        yaxis=dict(autorange="reversed"), # Lunes arriba
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, l=20, r=20, b=20),
        height=280,
        font={'family': 'Inter', 'color': '#333'}
    )
    
    return fig

# --- EJECUCIÓN PRINCIPAL ---
df = cargar_datos()

if df is None:
    st.error("⚠️ Esperando datos del bot... (Archivo csv no encontrado)")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    
    # Filtros
    origenes = df['origen'].unique()
    origen_sel = st.multiselect("Origen", origenes, default=origenes)
    
    aerolineas = df['nombre_aerolinea'].unique()
    aerolinea_sel = st.multiselect("Aerolínea", aerolineas, default=aerolineas)
    
    # Aplicar Filtros
    df_filtrado = df[
        (df['origen'].isin(origen_sel)) & 
        (df['nombre_aerolinea'].isin(aerolinea_sel))
    ]
    
    st.markdown("---")
    st.caption("v2.1 con Heatmap")

if df_filtrado.empty:
    st.warning("Sin datos para estos filtros.")
    st.stop()

# --- HEADER ---
st.title("Bali Flight Tracker")
st.markdown("Monitorización en tiempo real • Precios en EUR")
st.markdown("---")

# --- PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📊 Panorama General", "✈️ Análisis Aerolíneas", "📋 Datos Brutos"])

# === PESTAÑA 1: PANORAMA ===
with tab1:
    # 1. KPIs
    col1, col2, col3, col4 = st.columns(4)
    vuelo_barato = df_filtrado.loc[df_filtrado['precio_total'].idxmin()]

    col1.metric("Mejor Precio", f"{df_filtrado['precio_total'].min():.0f} €")
    col2.metric("Precio Medio", f"{df_filtrado['precio_total'].mean():.0f} €")
    col3.metric("Aerolínea Top", vuelo_barato['nombre_aerolinea'])
    col4.metric("Duración Mín.", f"{vuelo_barato['duracion_horas']:.1f} h")

    st.markdown("###") 

    # 2. CALENDAR HEATMAP (NUEVO)
    st.plotly_chart(plot_calendar_heatmap(df_filtrado), use_container_width=True)

    st.markdown("###")

    # 3. GRÁFICOS CLÁSICOS (Barras y Línea)
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 🗓️ Precios por Fecha")
        df_dias = df_filtrado.groupby('fecha_salida')['precio_total'].min().reset_index()
        fig_bar = px.bar(df_dias, x='fecha_salida', y='precio_total')
        fig_bar.update_traces(marker_color='#111111')
        fig_bar.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=20, b=20),
            font={'family': 'Inter', 'color': '#333'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        st.markdown("#### 📉 Evolución Temporal")
        COLOR_SCALE = ['#111111', '#555555', '#999999']
        fig_line = px.line(
            df_filtrado, x='fecha_consulta', y='precio_total', color='origen',
            color_discrete_sequence=COLOR_SCALE,
            markers=True
        )
        fig_line.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=20, r=20, t=20, b=20),
            font={'family': 'Inter', 'color': '#333'}
        )
        st.plotly_chart(fig_line, use_container_width=True)

# === PESTAÑA 2: AEROLÍNEAS ===
with tab2:
    st.markdown("#### ⏳ Calidad vs Precio")
    fig_scatter = px.scatter(
        df_filtrado, x='duracion_horas', y='precio_total',
        color='nombre_aerolinea',
        color_discrete_sequence=px.colors.sequential.Greys_r,
        size='precio_total',
        hover_data=['fecha_salida', 'escalas']
    )
    # Línea de referencia 20h
    fig_scatter.add_vline(x=20, line_dash="dash", line_color="#111111", annotation_text="20h")
    
    fig_scatter.update_layout(
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#F0F0F0'),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0'),
        font={'family': 'Inter', 'color': '#333'}
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### 🛫 Aerolíneas")
        df_pie = df_filtrado['nombre_aerolinea'].value_counts().reset_index()
        fig_pie = px.pie(
            df_pie, values='count', names='nombre_aerolinea',
            color_discrete_sequence=px.colors.sequential.Greys_r,
            hole=0.6
        )
        fig_pie.update_layout(template='plotly_white', showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)

# === PESTAÑA 3: DATOS ===
with tab3:
    st.markdown("#### 📋 Detalle de Vuelos")
    st.dataframe(
        df_filtrado[['fecha_salida', 'origen', 'nombre_aerolinea', 'precio_total', 'duracion_horas', 'escalas']]
        .sort_values("precio_total")
        .style.background_gradient(cmap='Greys', subset=['precio_total']),
        use_container_width=True,
        hide_index=True
    )
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
        st.warning(f"⚠️ Falta style.css")

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

# --- FUNCIÓN GRÁFICA: CALENDAR HEATMAP (Minimalist Style) ---
def plot_calendar_heatmap(df):
    # 1. Preparar datos
    df_cal = df.groupby('fecha_salida')['precio_total'].min().reset_index()
    
    # Metadatos
    df_cal['semana'] = df_cal['fecha_salida'].dt.isocalendar().week
    df_cal['dia_semana'] = df_cal['fecha_salida'].dt.dayofweek # 0=Lun
    df_cal['texto_fecha'] = df_cal['fecha_salida'].dt.strftime('%d %b')
    df_cal['precio_texto'] = df_cal['precio_total'].apply(lambda x: f"{x:.0f}€")
    
    # 2. Pivotar
    matriz_precios = df_cal.pivot(index='dia_semana', columns='semana', values='precio_total')
    matriz_precio_str = df_cal.pivot(index='dia_semana', columns='semana', values='precio_texto')
    matriz_fecha = df_cal.pivot(index='dia_semana', columns='semana', values='texto_fecha')
    
    # 3. Heatmap
    # Usamos escala de grises: Negro (#111) = Barato, Gris claro (#EEE) = Caro
    fig = go.Figure(data=go.Heatmap(
        z=matriz_precios,
        x=matriz_precios.columns,
        y=['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
        text=matriz_precio_str,
        customdata=matriz_fecha,
        texttemplate="%{text}", 
        textfont={"size": 11, "family": "Inter", "color": "white"}, # Texto blanco sobre fondo oscuro
        hovertemplate="<b>%{customdata}</b><br>Semana %{x}<br>Precio: %{z:.0f}€<extra></extra>",
        colorscale=[[0, '#111111'], [1, '#DDDDDD']], # Negro a Gris Claro
        showscale=False,
        xgap=4, # Huecos blancos entre cuadros (Look moderno)
        ygap=4
    ))
    
    fig.update_layout(
        title=dict(text="📅 Calendario de Precios (Negro = Más Barato)", font=dict(size=16, color="#111")),
        xaxis_title="",
        yaxis_title="",
        yaxis=dict(autorange="reversed", showticklabels=True), 
        xaxis=dict(showticklabels=False), # Ocultamos números de semana para limpiar
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, l=0, r=0, b=0),
        height=250,
        font={'family': 'Inter', 'color': '#333'}
    )
    
    return fig

# --- EJECUCIÓN PRINCIPAL ---
df = cargar_datos()

if df is None:
    st.error("⚠️ Esperando datos del bot...")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    origen_sel = st.multiselect("Origen", df['origen'].unique(), default=df['origen'].unique())
    aerolinea_sel = st.multiselect("Aerolínea", df['nombre_aerolinea'].unique(), default=df['nombre_aerolinea'].unique())
    df_filtrado = df[(df['origen'].isin(origen_sel)) & (df['nombre_aerolinea'].isin(aerolinea_sel))]
    st.markdown("---")
    st.caption("v2.2 Heatmap + Minimalist")

if df_filtrado.empty:
    st.warning("Sin datos.")
    st.stop()

# --- HEADER ---
st.title("Bali Flight Tracker")
st.markdown("Monitorización en tiempo real • Precios en EUR")
st.markdown("###") # Espaciador

# --- KPIS ---
col1, col2, col3, col4 = st.columns(4)
vuelo_barato = df_filtrado.loc[df_filtrado['precio_total'].idxmin()]

col1.metric("Mejor Precio", f"{df_filtrado['precio_total'].min():.0f} €")
col2.metric("Precio Medio", f"{df_filtrado['precio_total'].mean():.0f} €")
col3.metric("Aerolínea Top", vuelo_barato['nombre_aerolinea'])
col4.metric("Duración Mín.", f"{vuelo_barato['duracion_horas']:.1f} h")

st.markdown("###")

# --- PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📊 Panorama General", "✈️ Análisis Aerolíneas", "📋 Datos Brutos"])

# === PESTAÑA 1 ===
with tab1:
    # 1. CALENDARIO (AQUÍ ESTÁ LA MAGIA QUE FALTABA)
    st.plotly_chart(plot_calendar_heatmap(df_filtrado), use_container_width=True)
    
    st.markdown("###")
    
    # 2. GRÁFICOS INFERIORES
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 🗓️ Precios por Fecha")
        df_dias = df_filtrado.groupby('fecha_salida')['precio_total'].min().reset_index()
        fig_bar = px.bar(df_dias, x='fecha_salida', y='precio_total', text_auto='.0f')
        fig_bar.update_traces(marker_color='#111111')
        fig_bar.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=20),
            font={'family': 'Inter'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        st.markdown("#### 📉 Evolución Temporal")
        fig_line = px.line(
            df_filtrado, x='fecha_consulta', y='precio_total', color='origen',
            color_discrete_sequence=['#111111', '#999999'], markers=True
        )
        fig_line.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=0, r=0, t=20, b=20),
            font={'family': 'Inter'}
        )
        st.plotly_chart(fig_line, use_container_width=True)

# === PESTAÑA 2 ===
with tab2:
    st.markdown("#### ⏳ Calidad vs Precio")
    fig_scatter = px.scatter(
        df_filtrado, x='duracion_horas', y='precio_total',
        color='nombre_aerolinea',
        color_discrete_sequence=px.colors.sequential.Greys_r,
        size='precio_total'
    )
    fig_scatter.add_vline(x=20, line_dash="dash", line_color="#111111", annotation_text="20h")
    fig_scatter.update_layout(
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#F0F0F0'),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0'),
        font={'family': 'Inter'}
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### 🛫 Aerolíneas")
        df_pie = df_filtrado['nombre_aerolinea'].value_counts().reset_index()
        fig_pie = px.pie(
            df_pie, values='count', names='nombre_aerolinea',
            color_discrete_sequence=px.colors.sequential.Greys_r, hole=0.6
        )
        fig_pie.update_layout(template='plotly_white', showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)

# === PESTAÑA 3 ===
with tab3:
    st.markdown("#### 📋 Detalle de Vuelos")
    st.dataframe(
        df_filtrado[['fecha_salida', 'origen', 'nombre_aerolinea', 'precio_total', 'duracion_horas', 'escalas']]
        .sort_values("precio_total")
        .style.background_gradient(cmap='Greys', subset=['precio_total']),
        use_container_width=True,
        hide_index=True
    )
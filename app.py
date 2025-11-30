import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Bali Flight Tracker",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNCIÓN PARA CARGAR CSS EXTERNO ---
def cargar_css(nombre_archivo):
    with open(nombre_archivo) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Llamamos a la función cargando tu nuevo archivo
cargar_css("style.css")


# --- DICCIONARIO AEROLÍNEAS ---
AEROLINEAS_NOMBRES = {
    "QR": "Qatar Airways", "EK": "Emirates", "TK": "Turkish Airlines",
    "SQ": "Singapore Airlines", "CX": "Cathay Pacific", "EY": "Etihad",
    "KL": "KLM", "AF": "Air France", "SV": "Saudia"
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
    st.caption("v2.0 Minimalist Design")

if df_filtrado.empty:
    st.warning("Sin datos para estos filtros.")
    st.stop()

# --- HEADER ---
st.title("Bali Flight Tracker")
st.markdown("Monitorización en tiempo real • Precios en EUR")
st.markdown("---")

# --- KPIS (TARJETAS) ---
col1, col2, col3, col4 = st.columns(4)
vuelo_barato = df_filtrado.loc[df_filtrado['precio_total'].idxmin()]

col1.metric("Mejor Precio", f"{df_filtrado['precio_total'].min():.0f} €")
col2.metric("Precio Medio", f"{df_filtrado['precio_total'].mean():.0f} €")
col3.metric("Aerolínea Top", vuelo_barato['nombre_aerolinea'])
col4.metric("Duración Mín.", f"{vuelo_barato['duracion_horas']:.1f} h")

st.markdown("###") # Espacio

# --- GRÁFICOS (ESTILO MONOCROMO) ---

# Paleta de grises elegante
COLOR_SCALE = ['#111111', '#555555', '#999999', '#CCCCCC', '#E0E0E0']

c1, c2 = st.columns(2)

with c1:
    st.markdown("#### 🗓️ Precios por Fecha")
    df_dias = df_filtrado.groupby('fecha_salida')['precio_total'].min().reset_index()
    
    # Gráfico minimalista: Fondo blanco, barras negras/grises
    fig_bar = px.bar(
        df_dias, x='fecha_salida', y='precio_total',
        text_auto='.0f'
    )
    fig_bar.update_traces(marker_color='#111111', textfont_color='white')
    fig_bar.update_layout(
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)', # Transparente para que tome el fondo de la "tarjeta"
        plot_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Inter', 'color': '#333'},
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0'),
        xaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    st.markdown("#### 📉 Evolución Temporal")
    fig_line = px.line(
        df_filtrado, x='fecha_consulta', y='precio_total', color='origen',
        color_discrete_sequence=COLOR_SCALE, # Usar grises
        markers=True
    )
    fig_line.update_layout(
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Inter', 'color': '#333'},
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_line, use_container_width=True)

# SEGUNDA FILA
c3, c4 = st.columns(2)

with c3:
    st.markdown("#### ⏳ Calidad vs Precio")
    fig_scatter = px.scatter(
        df_filtrado, x='duracion_horas', y='precio_total',
        color='nombre_aerolinea',
        color_discrete_sequence=COLOR_SCALE,
        size='precio_total'
    )
    fig_scatter.update_layout(
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0'),
        xaxis=dict(showgrid=True, gridcolor='#F0F0F0')
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with c4:
    st.markdown("#### 🛫 Aerolíneas")
    df_pie = df_filtrado['nombre_aerolinea'].value_counts().reset_index()
    df_pie.columns = ['aerolinea', 'count']
    
    fig_pie = px.pie(
        df_pie, values='count', names='aerolinea',
        color_discrete_sequence=COLOR_SCALE,
        hole=0.6 # Donut chart es más moderno
    )
    fig_pie.update_layout(
        template='plotly_white',
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="v", yanchor="middle", y=0.5)
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# TABLA LIMPIA
st.markdown("#### 📋 Detalle de Vuelos")
st.dataframe(
    df_filtrado[['fecha_salida', 'origen', 'nombre_aerolinea', 'precio_total', 'duracion_horas', 'escalas']]
    .sort_values("precio_total")
    .style.background_gradient(cmap='Greys', subset=['precio_total']),
    use_container_width=True,
    hide_index=True
)
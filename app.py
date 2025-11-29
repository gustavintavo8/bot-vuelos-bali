import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Bali Flight Tracker Pro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DICCIONARIO DE AEROLÍNEAS (Para que se vea bonito) ---
AEROLINEAS_NOMBRES = {
    "QR": "Qatar Airways",
    "EK": "Emirates",
    "TK": "Turkish Airlines",
    "SQ": "Singapore Airlines",
    "CX": "Cathay Pacific",
    "EY": "Etihad Airways",
    "KL": "KLM Royal Dutch",
    "AF": "Air France",
    "SV": "Saudia",
    "GA": "Garuda Indonesia",
    "MH": "Malaysia Airlines",
    "TG": "Thai Airways",
    "CI": "China Airlines",
    "MU": "China Eastern",
    "CZ": "China Southern"
}

def get_nombre_aerolinea(codigo):
    return AEROLINEAS_NOMBRES.get(codigo, codigo)  # Si no está, devuelve el código

# --- CARGA DE DATOS ---
ARCHIVO_CSV = "historial_extendido.csv"

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_csv(ARCHIVO_CSV)
        
        # Conversión de fechas
        df['fecha_consulta'] = pd.to_datetime(df['fecha_consulta'])
        df['fecha_salida'] = pd.to_datetime(df['fecha_salida'])
        
        # Crear columna de nombre completo de aerolínea
        df['nombre_aerolinea'] = df['aerolinea'].apply(get_nombre_aerolinea)
        
        # Calcular horas para visualización (más fácil de leer que minutos)
        df['duracion_horas'] = df['duracion_minutos'] / 60
        
        return df
    except FileNotFoundError:
        return None

# --- INTERFAZ PRINCIPAL ---

st.title("🏝️ Bali Flight Intelligence")
st.markdown("""
<style>
    .big-font { font-size:20px !important; }
</style>
""", unsafe_allow_html=True)
st.markdown('<p class="big-font">Monitorización avanzada de precios y tendencias para tu viaje a Indonesia.</p>', unsafe_allow_html=True)

df = cargar_datos()

if df is None:
    st.error("⚠️ No se ha encontrado el archivo de datos ('historial_extendido.csv'). Asegúrate de que el bot ha ejecutado al menos una vez.")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
with st.sidebar:
    st.header("🔍 Filtros de Búsqueda")
    
    # Filtro Origen
    origenes_disponibles = df['origen'].unique()
    origen_sel = st.multiselect("Aeropuerto de Origen", origenes_disponibles, default=origenes_disponibles)
    
    # Filtro Aerolínea
    aerolineas_disponibles = df['nombre_aerolinea'].unique()
    aerolinea_sel = st.multiselect("Aerolíneas", aerolineas_disponibles, default=aerolineas_disponibles)
    
    # Filtro Escalas
    escalas_sel = st.slider("Máximo de Escalas", 0, 3, 2, help="0 = Directo (Raro), 1 = Una parada")

    # Aplicar filtros
    df_filtrado = df[
        (df['origen'].isin(origen_sel)) & 
        (df['nombre_aerolinea'].isin(aerolinea_sel)) &
        (df['escalas'] <= escalas_sel)
    ]
    
    st.markdown("---")
    st.caption(f"📅 Última actualización: {df['fecha_consulta'].max().strftime('%d/%m/%Y %H:%M')}")
    st.caption(f"📊 Total registros analizados: {len(df)}")

if df_filtrado.empty:
    st.warning("No hay vuelos que coincidan con tus filtros.")
    st.stop()

# --- PESTAÑAS (TABS) ---
tab1, tab2, tab3 = st.tabs(["📊 Panorama General", "✈️ Análisis de Aerolíneas", "📋 Datos Detallados"])

# === PESTAÑA 1: PANORAMA ===
with tab1:
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    mejor_precio = df_filtrado['precio_total'].min()
    precio_promedio = df_filtrado['precio_total'].mean()
    vuelo_barato = df_filtrado.loc[df_filtrado['precio_total'].idxmin()]
    
    col1.metric("💎 Precio Mínimo", f"{mejor_precio:.0f} €", help="El precio más bajo encontrado en todo el historial.")
    col2.metric("📈 Precio Medio", f"{precio_promedio:.0f} €", help="Media de todos los vuelos rastreados.")
    col3.metric("🏆 Mejor Aerolínea", vuelo_barato['nombre_aerolinea'], help="La compañía que ofrece el vuelo más barato actualmente.")
    col4.metric("⏱️ Duración Óptima", f"{vuelo_barato['duracion_horas']:.1f} h", help="Duración del vuelo más barato.")

    st.divider()

    # GRÁFICOS PRINCIPALES
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🗓️ ¿Qué día es más barato volar?")
        # Agrupar por fecha de salida y coger el mínimo
        df_dias = df_filtrado.groupby('fecha_salida')['precio_total'].min().reset_index()
        
        fig_bar = px.bar(
            df_dias, x='fecha_salida', y='precio_total',
            color='precio_total', color_continuous_scale='Bluyl',
            labels={'fecha_salida': 'Fecha de Salida', 'precio_total': 'Mejor Precio (€)'},
            text_auto='.0f'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.info("💡 **Consejo:** Las barras más claras indican los días más baratos para iniciar tu viaje.")

    with c2:
        st.subheader("📉 Tendencia de Precios")
        # Evolución temporal
        fig_line = px.line(
            df_filtrado, x='fecha_consulta', y='precio_total', color='origen',
            markers=True,
            labels={'fecha_consulta': 'Fecha de Rastreo', 'precio_total': 'Precio (€)'},
            title="Evolución del precio detectado por el bot"
        )
        st.plotly_chart(fig_line, use_container_width=True)


# === PESTAÑA 2: AEROLÍNEAS ===
with tab2:
    st.subheader("🆚 Comparativa: Calidad vs Precio")
    st.markdown("Este gráfico es fundamental. Buscamos vuelos en la **zona inferior izquierda** (Baratos y Rápidos).")
    
    fig_scatter = px.scatter(
        df_filtrado, 
        x='duracion_horas', 
        y='precio_total',
        color='nombre_aerolinea',
        size='precio_total', # Las burbujas más grandes son más caras
        hover_data=['fecha_salida', 'escalas', 'numero_vuelo'],
        labels={'duracion_horas': 'Duración Total (Horas)', 'precio_total': 'Precio (€)', 'nombre_aerolinea': 'Aerolínea'}
    )
    # Añadir línea de referencia de 20 horas
    fig_scatter.add_vline(x=20, line_width=1, line_dash="dash", line_color="green", annotation_text="Frontera Rápida (20h)")
    
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    c3, c4 = st.columns(2)
    
    with c3:
        st.subheader("💰 Rango de Precios por Compañía")
        fig_box = px.box(
            df_filtrado, x='nombre_aerolinea', y='precio_total', color='nombre_aerolinea',
            points="all",
            labels={'nombre_aerolinea': '', 'precio_total': 'Precio (€)'}
        )
        st.plotly_chart(fig_box, use_container_width=True)
        
    with c4:
        st.subheader("🛑 ¿Cuántas escalas suelen hacer?")
        # Gráfico de pastel de escalas
        df_escalas = df_filtrado['escalas'].value_counts().reset_index()
        df_escalas.columns = ['escalas', 'cantidad']
        df_escalas['escalas'] = df_escalas['escalas'].astype(str) + " Escala(s)"
        
        fig_pie = px.pie(
            df_escalas, values='cantidad', names='escalas',
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# === PESTAÑA 3: DATOS ===
with tab3:
    st.subheader("📋 Tabla de Datos Completa")
    st.markdown("Aquí tienes todos los datos en bruto por si quieres revisarlos manualmente.")
    
    # Formatear la tabla para que sea bonita
    st.dataframe(
        df_filtrado.sort_values(by="precio_total", ascending=True).style.format({
            "precio_total": "{:.2f} €",
            "precio_base": "{:.2f} €",
            "impuestos": "{:.2f} €",
            "duracion_minutos": "{:.0f} min"
        }),
        use_container_width=True,
        height=500
    )
    
    # Botón de descarga
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar datos filtrados en CSV",
        data=csv,
        file_name='vuelos_bali_filtrados.csv',
        mime='text/csv',
    )
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

# --- CONSTANTES ---
PRECIO_OBJETIVO = 800  # 🎯 Precio objetivo para alertas
ASIENTOS_CRITICOS = 5  # ⚠️ Umbral de asientos para alertas

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
        df['porcentaje_impuestos'] = (df['impuestos'] / df['precio_total']) * 100
        return df
    except FileNotFoundError:
        return None

# --- 🏆 FUNCIÓN: CALCULAR SCORE DE VUELO ---
def calcular_score_vuelo(row):
    """Calcula un score de 0-100 basado en múltiples factores"""
    # Normalizar precio (invertido: menor precio = mejor score)
    precio_norm = 100 - ((row['precio_total'] - 500) / 10)
    precio_norm = max(0, min(100, precio_norm))
    
    # Normalizar duración (invertido: menor duración = mejor)
    duracion_norm = 100 - ((row['duracion_horas'] - 10) * 5)
    duracion_norm = max(0, min(100, duracion_norm))
    
    # Horario (preferencia por salidas entre 8h-22h)
    try:
        hora_salida = int(row['hora_salida'].split(':')[0])
        if 8 <= hora_salida <= 22:
            horario_score = 100
        else:
            horario_score = 50
    except:
        horario_score = 50
    
    # Asientos disponibles (más asientos = mejor)
    try:
        asientos = int(row['asientos_disponibles'])
        asientos_score = min(100, asientos * 20)
    except:
        asientos_score = 50
    
    # Pesos
    score_total = (
        precio_norm * 0.4 +
        duracion_norm * 0.3 +
        horario_score * 0.2 +
        asientos_score * 0.1
    )
    
    return round(score_total, 1)

# --- 🏆 FUNCIÓN: OBTENER TOP OFERTAS ---
def obtener_top_ofertas(df, n=3):
    """Obtiene los mejores N vuelos según scoring"""
    if df.empty:
        return pd.DataFrame()
    df_copy = df.copy()
    df_copy['score'] = df_copy.apply(calcular_score_vuelo, axis=1)
    top = df_copy.nlargest(n, 'score')
    return top

# --- 📈 FUNCIÓN: CALCULAR TENDENCIA ---
def calcular_tendencia_precio(df, fecha_salida):
    """Calcula la tendencia de precio para una fecha específica"""
    df_fecha = df[df['fecha_salida'] == fecha_salida].sort_values('fecha_consulta')
    
    if len(df_fecha) < 2:
        return "➡️", 0, "Datos insuficientes"
    
    precios = df_fecha['precio_total'].values
    primer_precio = precios[0]
    ultimo_precio = precios[-1]
    cambio = ultimo_precio - primer_precio
    cambio_pct = (cambio / primer_precio) * 100
    
    if cambio_pct < -2:
        return "📉", cambio_pct, "¡Compra ahora!"
    elif cambio_pct > 2:
        return "📈", cambio_pct, "Espera un poco"
    else:
        return "➡️", cambio_pct, "Precio estable"

# --- 💰 FUNCIÓN: GRÁFICO IMPUESTOS ---
def crear_grafico_impuestos(df):
    """Crea gráfico de barras apiladas: precio base vs impuestos"""
    df_agg = df.groupby('nombre_aerolinea').agg({
        'precio_base': 'mean',
        'impuestos': 'mean',
        'porcentaje_impuestos': 'mean'
    }).reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Precio Base',
        x=df_agg['nombre_aerolinea'],
        y=df_agg['precio_base'],
        marker_color='#111111',
        text=df_agg['precio_base'].round(0),
        textposition='inside',
        textfont=dict(color='white')
    ))
    
    fig.add_trace(go.Bar(
        name='Impuestos',
        x=df_agg['nombre_aerolinea'],
        y=df_agg['impuestos'],
        marker_color='#999999',
        text=df_agg['impuestos'].round(0),
        textposition='inside',
        textfont=dict(color='white')
    ))
    
    fig.update_layout(
        barmode='stack',
        title=dict(text="💰 Desglose: Precio Base vs Impuestos", font=dict(size=16, color="#111")),
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title="",
        yaxis_title="Precio (€)",
        font={'family': 'Inter'},
        showlegend=True,
        legend=dict(orientation="h", y=1.1)
    )
    
    return fig

# --- FUNCIÓN GRÁFICA: CALENDAR HEATMAP ---
def plot_calendar_heatmap(df):
    df_cal = df.groupby('fecha_salida')['precio_total'].min().reset_index()
    
    df_cal['semana'] = df_cal['fecha_salida'].dt.isocalendar().week
    df_cal['dia_semana'] = df_cal['fecha_salida'].dt.dayofweek
    df_cal['fecha_str'] = df_cal['fecha_salida'].dt.strftime('%d-%b')
    
    pivot_precio = df_cal.pivot(index='dia_semana', columns='semana', values='precio_total')
    pivot_fecha = df_cal.pivot(index='dia_semana', columns='semana', values='fecha_str')
    
    if not df_cal.empty:
        min_sem = int(df_cal['semana'].min())
        max_sem = int(df_cal['semana'].max())
        semanas = list(range(min_sem, max_sem + 1))
        
        pivot_precio = pivot_precio.reindex(index=range(7), columns=semanas)
        pivot_fecha = pivot_fecha.reindex(index=range(7), columns=semanas)
    else:
        semanas = []
        
    z_values = pivot_precio.values
    customdata = pivot_fecha.fillna('').values
    text_values = pivot_precio.applymap(lambda x: f"{x:.0f}€" if pd.notnull(x) else "").values

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=semanas,
        y=['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
        text=text_values,
        customdata=customdata,
        texttemplate="%{text}", 
        textfont={"size": 11, "family": "Inter", "color": "white"},
        hovertemplate="<b>%{customdata}</b><br>Semana %{x}<br>Precio: %{z:.0f}€<extra></extra>",
        colorscale=[[0, '#111111'], [1, '#DDDDDD']], 
        showscale=False,
        xgap=4, 
        ygap=4
    ))
    
    fig.update_layout(
        title=dict(text="📅 Calendario de Precios (Negro = Más Barato)", font=dict(size=16, color="#111")),
        xaxis_title="",
        yaxis_title="",
        yaxis=dict(autorange="reversed", showticklabels=True), 
        xaxis=dict(showticklabels=False), 
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, l=0, r=0, b=0),
        height=250,
        font={'family': 'Inter', 'color': '#333'}
    )
    
    return fig

# ========== EJECUCIÓN PRINCIPAL ==========

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
    st.markdown("### 🎯 Precio Objetivo")
    st.metric("Target", f"{PRECIO_OBJETIVO} €", help="Precio objetivo para alertas especiales")
    
    vuelos_bajo_objetivo = len(df_filtrado[df_filtrado['precio_total'] < PRECIO_OBJETIVO])
    if vuelos_bajo_objetivo > 0:
        st.success(f"🔥 {vuelos_bajo_objetivo} vuelo(s) bajo objetivo!")
    else:
        st.info("Sin vuelos bajo objetivo")
    
    st.markdown("---")
    st.caption("v3.0 Enhanced Dashboard")

if df_filtrado.empty:
    st.warning("Sin datos.")
    st.stop()

# --- HEADER ---
st.title("Bali Flight Tracker")
st.markdown("Monitorización en tiempo real • Precios en EUR")
st.markdown("###")

# --- 🎫 ALERTAS DE DISPONIBILIDAD ---
vuelos_criticos = df_filtrado[df_filtrado['asientos_disponibles'] <= ASIENTOS_CRITICOS]
if not vuelos_criticos.empty:
    st.warning(f"⚠️ **ALERTA DE DISPONIBILIDAD**: {len(vuelos_criticos)} vuelo(s) con menos de {ASIENTOS_CRITICOS} asientos disponibles")

# --- KPIS MEJORADOS ---
col1, col2, col3, col4, col5 = st.columns(5)
vuelo_barato = df_filtrado.loc[df_filtrado['precio_total'].idxmin()]

delta_objetivo = vuelo_barato['precio_total'] - PRECIO_OBJETIVO
delta_color = "inverse" if delta_objetivo < 0 else "normal"

col1.metric("Mejor Precio", f"{df_filtrado['precio_total'].min():.0f} €", 
            delta=f"{delta_objetivo:.0f}€ vs objetivo", delta_color=delta_color)
col2.metric("Precio Medio", f"{df_filtrado['precio_total'].mean():.0f} €")
col3.metric("Aerolínea Top", vuelo_barato['nombre_aerolinea'])
col4.metric("Duración Mín.", f"{vuelo_barato['duracion_horas']:.1f} h")
col5.metric("Asientos Disp.", f"{int(vuelo_barato['asientos_disponibles'])}", 
            help="Asientos disponibles en el vuelo más barato")

st.markdown("###")

# --- PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📊 Panorama General", "✈️ Análisis Aerolíneas", "📋 Datos Brutos"])

# ========== PESTAÑA 1: PANORAMA GENERAL ==========
with tab1:
    # 🏆 TOP 3 MEJORES OFERTAS
    st.markdown("### 🏆 Top 3 Mejores Ofertas")
    top_ofertas = obtener_top_ofertas(df_filtrado, 3)
    
    if not top_ofertas.empty:
        cols_ofertas = st.columns(3)
        medallas = ["🥇", "🥈", "🥉"]
        
        for idx, (_, vuelo) in enumerate(top_ofertas.iterrows()):
            with cols_ofertas[idx]:
                border_color = "#00AA00" if vuelo['precio_total'] < PRECIO_OBJETIVO else "#111111"
                
                st.markdown(f"""
                <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 15px; background: #f9f9f9;">
                    <h3 style="margin:0;">{medallas[idx]} Score: {vuelo['score']}/100</h3>
                    <p style="font-size: 24px; font-weight: bold; margin: 5px 0;">{vuelo['precio_total']:.0f}€</p>
                    <p style="margin: 5px 0;">✈️ {vuelo['nombre_aerolinea']}</p>
                    <p style="margin: 5px 0;">📅 {vuelo['fecha_salida'].strftime('%d-%b-%Y')}</p>
                    <p style="margin: 5px 0;">⏱️ {vuelo['duracion_horas']:.1f}h | 🎫 {int(vuelo['asientos_disponibles'])} asientos</p>
                    <p style="margin: 5px 0;">🛫 {vuelo['origen']} → DPS</p>
                </div>
                """, unsafe_allow_html=True)
                
                razones = []
                if vuelo['precio_total'] < PRECIO_OBJETIVO:
                    razones.append("🔥 Bajo precio objetivo")
                if vuelo['duracion_horas'] < 18:
                    razones.append("⚡ Duración corta")
                if int(vuelo['asientos_disponibles']) > 5:
                    razones.append("✅ Buena disponibilidad")
                
                if razones:
                    st.caption("**Por qué es bueno:** " + " • ".join(razones))
    
    st.markdown("###")
    
    # 📈 TENDENCIAS DE PRECIO
    st.markdown("### 📈 Tendencias de Precio por Fecha")
    
    fechas_unicas = sorted(df_filtrado['fecha_salida'].unique())
    if len(fechas_unicas) > 0:
        cols_trend = st.columns(min(len(fechas_unicas), 5))
        
        for idx, fecha in enumerate(fechas_unicas[:5]):
            with cols_trend[idx % 5]:
                icono, cambio_pct, recomendacion = calcular_tendencia_precio(df_filtrado, fecha)
                precio_actual = df_filtrado[df_filtrado['fecha_salida'] == fecha]['precio_total'].iloc[-1]
                
                st.metric(
                    label=f"{icono} {fecha.strftime('%d-%b')}",
                    value=f"{precio_actual:.0f}€",
                    delta=f"{cambio_pct:+.1f}%"
                )
                st.caption(recomendacion)
    
    st.markdown("###")
    
    # CALENDARIO
    st.plotly_chart(plot_calendar_heatmap(df_filtrado), use_container_width=True)
    
    st.markdown("###")
    
    # GRÁFICOS INFERIORES
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 🗓️ Precios por Fecha")
        df_dias = df_filtrado.groupby('fecha_salida')['precio_total'].min().reset_index()
        fig_bar = px.bar(df_dias, x='fecha_salida', y='precio_total', text_auto='.0f')
        fig_bar.update_traces(marker_color='#111111')
        
        fig_bar.add_hline(y=PRECIO_OBJETIVO, line_dash="dash", line_color="red", 
                         annotation_text=f"Objetivo: {PRECIO_OBJETIVO}€", 
                         annotation_position="right")
        
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
        
        fig_line.add_hline(y=PRECIO_OBJETIVO, line_dash="dash", line_color="red",
                          annotation_text=f"Objetivo: {PRECIO_OBJETIVO}€")
        
        fig_line.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=0, r=0, t=20, b=20),
            font={'family': 'Inter'}
        )
        st.plotly_chart(fig_line, use_container_width=True)

# ========== PESTAÑA 2: ANÁLISIS AEROLÍNEAS ==========
with tab2:
    # 💰 ANÁLISIS DE IMPUESTOS
    st.plotly_chart(crear_grafico_impuestos(df_filtrado), use_container_width=True)
    
    col_imp1, col_imp2, col_imp3 = st.columns(3)
    col_imp1.metric("Impuestos Promedio", f"{df_filtrado['impuestos'].mean():.0f}€")
    col_imp2.metric("% Impuestos Promedio", f"{df_filtrado['porcentaje_impuestos'].mean():.1f}%")
    
    aerolinea_menos_impuestos = df_filtrado.groupby('nombre_aerolinea')['porcentaje_impuestos'].mean().idxmin()
    col_imp3.metric("Menos Impuestos", aerolinea_menos_impuestos)
    
    st.markdown("###")
    
    st.markdown("#### ⏳ Calidad vs Precio")
    fig_scatter = px.scatter(
        df_filtrado, x='duracion_horas', y='precio_total',
        color='nombre_aerolinea',
        color_discrete_sequence=px.colors.sequential.Greys_r,
        size='precio_total',
        hover_data=['fecha_salida', 'asientos_disponibles']
    )
    fig_scatter.add_vline(x=20, line_dash="dash", line_color="#111111", annotation_text="20h")
    fig_scatter.add_hline(y=PRECIO_OBJETIVO, line_dash="dash", line_color="red", 
                         annotation_text=f"Objetivo: {PRECIO_OBJETIVO}€")
    
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
    
    with c4:
        st.markdown("#### 🎫 Disponibilidad de Asientos")
        df_asientos = df_filtrado.groupby('nombre_aerolinea')['asientos_disponibles'].mean().reset_index()
        fig_asientos = px.bar(df_asientos, x='nombre_aerolinea', y='asientos_disponibles',
                             color='asientos_disponibles',
                             color_continuous_scale=['#FF0000', '#FFAA00', '#00AA00'])
        fig_asientos.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            font={'family': 'Inter'}
        )
        st.plotly_chart(fig_asientos, use_container_width=True)

# ========== PESTAÑA 3: DATOS BRUTOS ==========
with tab3:
    st.markdown("#### 📋 Detalle de Vuelos")
    
    df_display = df_filtrado.copy()
    df_display['score'] = df_display.apply(calcular_score_vuelo, axis=1)
    df_display['🎯 Bajo Objetivo'] = df_display['precio_total'] < PRECIO_OBJETIVO
    df_display['🎯 Bajo Objetivo'] = df_display['🎯 Bajo Objetivo'].map({True: '✅', False: '❌'})
    
    df_display = df_display[['fecha_salida', 'origen', 'nombre_aerolinea', 'precio_total', 
                             'duracion_horas', 'escalas', 'asientos_disponibles', 'score', '🎯 Bajo Objetivo']].sort_values("score", ascending=False)
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "fecha_salida": st.column_config.DateColumn("Fecha Salida", format="DD-MM-YYYY"),
            "precio_total": st.column_config.NumberColumn("Precio", format="%.0f €"),
            "duracion_horas": st.column_config.NumberColumn("Duración", format="%.1f h"),
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
            "asientos_disponibles": st.column_config.NumberColumn("Asientos", format="%d")
        }
    )
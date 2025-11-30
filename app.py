import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Bali Flight Tracker",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONSTANTES ---
PRECIO_OBJETIVO_DEFAULT = 750
ASIENTOS_CRITICOS = 5

# --- CARGAR AEROPUERTOS ---
@st.cache_data
def cargar_aeropuertos():
    try:
        with open('airports.json', 'r') as f:
            return json.load(f)
    except:
        return {}

AIRPORTS = cargar_aeropuertos()

# --- FUNCIÓN PARA CARGAR CSS ---
def cargar_css(nombre_archivo):
    try:
        with open(nombre_archivo) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

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
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_csv("historial_extendido.csv")
        df['fecha_consulta'] = pd.to_datetime(df['fecha_consulta'])
        df['fecha_salida'] = pd.to_datetime(df['fecha_salida'])
        df['nombre_aerolinea'] = df['aerolinea'].apply(get_nombre_aerolinea)
        df['duracion_horas'] = df['duracion_minutos'] / 60
        df['porcentaje_impuestos'] = (df['impuestos'] / df['precio_total']) * 100
        return df
    except FileNotFoundError:
        return None

# --- FUNCIONES DE SCORING ---
def calcular_score_vuelo(row):
    precio_norm = 100 - ((row['precio_total'] - 500) / 10)
    precio_norm = max(0, min(100, precio_norm))
    
    duracion_norm = 100 - ((row['duracion_horas'] - 10) * 5)
    duracion_norm = max(0, min(100, duracion_norm))
    
    try:
        hora_salida = int(row['hora_salida'].split(':')[0])
        horario_score = 100 if 8 <= hora_salida <= 22 else 50
    except:
        horario_score = 50
    
    try:
        asientos = int(row['asientos_disponibles'])
        asientos_score = min(100, asientos * 20)
    except:
        asientos_score = 50
    
    score_total = (precio_norm * 0.4 + duracion_norm * 0.3 + horario_score * 0.2 + asientos_score * 0.1)
    return round(score_total, 1)

def obtener_top_ofertas(df, n=3):
    if df.empty:
        return pd.DataFrame()
    df_copy = df.copy()
    df_copy['score'] = df_copy.apply(calcular_score_vuelo, axis=1)
    return df_copy.nlargest(n, 'score')

# --- PREDICCIÓN DE PRECIOS ---
def predecir_tendencia(df, fecha_salida):
    df_fecha = df[df['fecha_salida'] == fecha_salida].sort_values('fecha_consulta')
    
    if len(df_fecha) < 2:
        return "➡️", 0, "Datos insuficientes", None
    
    precios = df_fecha['precio_total'].values
    cambio = precios[-1] - precios[0]
    cambio_pct = (cambio / precios[0]) * 100
    
    # Predicción simple: proyectar tendencia 7 días
    prediccion = precios[-1] + (cambio * 0.5)  # Asume 50% de la tendencia continúa
    
    if cambio_pct < -2:
        return "📉", cambio_pct, "¡Compra ahora!", prediccion
    elif cambio_pct > 2:
        return "📈", cambio_pct, "Espera un poco", prediccion
    else:
        return "➡️", cambio_pct, "Precio estable", prediccion

# --- SISTEMA DE ALERTAS ---
def check_alertas(df, config):
    alertas = []
    vuelos_alertados = df.copy()
    
    if config['precio_max'] > 0:
        mask = vuelos_alertados['precio_total'] < config['precio_max']
        if mask.sum() > 0:
            alertas.append(f"🔥 {mask.sum()} vuelo(s) bajo {config['precio_max']}€")
            vuelos_alertados.loc[mask, 'alerta_precio'] = True
    
    if config['duracion_max'] > 0:
        mask = vuelos_alertados['duracion_horas'] < config['duracion_max']
        if mask.sum() > 0:
            alertas.append(f"⚡ {mask.sum()} vuelo(s) < {config['duracion_max']}h")
            vuelos_alertados.loc[mask, 'alerta_duracion'] = True
    
    if config['score_min'] > 0:
        vuelos_alertados['score'] = vuelos_alertados.apply(calcular_score_vuelo, axis=1)
        mask = vuelos_alertados['score'] > config['score_min']
        if mask.sum() > 0:
            alertas.append(f"⭐ {mask.sum()} vuelo(s) score > {config['score_min']}")
            vuelos_alertados.loc[mask, 'alerta_score'] = True
    
    return alertas, vuelos_alertados

# --- MAPA DE RUTAS ---
def crear_mapa_rutas(df):
    fig = go.Figure()
    
    # Colores por rango de precio
    def get_color(precio):
        if precio < 800:
            return '#00FF00'  # Verde
        elif precio < 900:
            return '#FFFF00'  # Amarillo
        else:
            return '#FF0000'  # Rojo
    
    rutas_unicas = {}
    
    for _, vuelo in df.iterrows():
        # Parsear ruta
        if pd.isna(vuelo['aeropuertos_escala']) or vuelo['aeropuertos_escala'] == '':
            # Vuelo directo
            ruta = [vuelo['origen'], vuelo['destino']]
        else:
            # Con escalas
            escalas = vuelo['aeropuertos_escala'].split(',')
            ruta = [vuelo['origen']] + escalas + [vuelo['destino']]
        
        ruta_key = '-'.join(ruta)
        precio = vuelo['precio_total']
        
        if ruta_key not in rutas_unicas or precio < rutas_unicas[ruta_key]['precio']:
            rutas_unicas[ruta_key] = {'ruta': ruta, 'precio': precio}
    
    # Dibujar rutas
    for ruta_info in rutas_unicas.values():
        ruta = ruta_info['ruta']
        precio = ruta_info['precio']
        color = get_color(precio)
        
        lons = []
        lats = []
        nombres = []
        
        for airport_code in ruta:
            if airport_code in AIRPORTS:
                lons.append(AIRPORTS[airport_code]['lon'])
                lats.append(AIRPORTS[airport_code]['lat'])
                nombres.append(AIRPORTS[airport_code]['name'])
        
        if len(lons) >= 2:
            # Línea de ruta
            fig.add_trace(go.Scattergeo(
                lon=lons,
                lat=lats,
                mode='lines+markers',
                line=dict(width=2, color=color),
                marker=dict(size=8, color=color),
                name=f"{ruta[0]}→{ruta[-1]} ({precio:.0f}€)",
                hovertemplate='<b>%{text}</b><br>Precio: ' + f'{precio:.0f}€<extra></extra>',
                text=nombres
            ))
    
    fig.update_geos(
        projection_type="natural earth",
        showcountries=True,
        showcoastlines=True,
        showland=True,
        landcolor='rgb(243, 243, 243)',
        coastlinecolor='rgb(204, 204, 204)',
        countrycolor='rgb(204, 204, 204)',
        lataxis_range=[-20, 60],
        lonaxis_range=[-20, 130]
    )
    
    fig.update_layout(
        title=dict(text="🗺️ Mapa de Rutas a Bali", font=dict(size=20, color="#111")),
        showlegend=True,
        legend=dict(orientation="v", y=0.5),
        height=600,
        margin=dict(l=0, r=0, t=40, b=0),
        font={'family': 'Inter'}
    )
    
    return fig

# --- EXPORTAR FUNCIONES ---
def exportar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Hoja 1: Resumen
        resumen = pd.DataFrame({
            'Métrica': ['Mejor Precio', 'Precio Medio', 'Vuelos Totales', 'Aerolíneas'],
            'Valor': [
                f"{df['precio_total'].min():.0f}€",
                f"{df['precio_total'].mean():.0f}€",
                len(df),
                df['nombre_aerolinea'].nunique()
            ]
        })
        resumen.to_excel(writer, sheet_name='Resumen', index=False)
        
        # Hoja 2: Todos los vuelos
        df_export = df[['fecha_salida', 'origen', 'nombre_aerolinea', 'precio_total', 
                       'duracion_horas', 'escalas', 'asientos_disponibles']].copy()
        df_export.to_excel(writer, sheet_name='Vuelos', index=False)
    
    output.seek(0)
    return output

# --- GRÁFICOS ---
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
        z=z_values, x=semanas,
        y=['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
        text=text_values, customdata=customdata,
        texttemplate="%{text}", 
        textfont={"size": 11, "family": "Inter", "color": "white"},
        hovertemplate="<b>%{customdata}</b><br>Precio: %{z:.0f}€<extra></extra>",
        colorscale=[[0, '#111111'], [1, '#DDDDDD']], 
        showscale=False, xgap=4, ygap=4
    ))
    
    fig.update_layout(
        title=dict(text="📅 Calendario de Precios", font=dict(size=16, color="#111")),
        yaxis=dict(autorange="reversed"), xaxis=dict(showticklabels=False),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, l=0, r=0, b=0), height=250, font={'family': 'Inter'}
    )
    return fig

def crear_grafico_impuestos(df):
    df_agg = df.groupby('nombre_aerolinea').agg({
        'precio_base': 'mean', 'impuestos': 'mean'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Precio Base', x=df_agg['nombre_aerolinea'], 
                         y=df_agg['precio_base'], marker_color='#111111'))
    fig.add_trace(go.Bar(name='Impuestos', x=df_agg['nombre_aerolinea'], 
                         y=df_agg['impuestos'], marker_color='#999999'))
    
    fig.update_layout(barmode='stack', title="💰 Desglose de Precios",
                     template='plotly_white', paper_bgcolor='rgba(0,0,0,0)',
                     font={'family': 'Inter'}, legend=dict(orientation="h", y=1.1))
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
    aerolinea_sel = st.multiselect("Aerolínea", df['nombre_aerolinea'].unique(), 
                                   default=df['nombre_aerolinea'].unique())
    df_filtrado = df[(df['origen'].isin(origen_sel)) & (df['nombre_aerolinea'].isin(aerolinea_sel))]
    
    st.markdown("---")
    st.markdown("### 🎯 Precio Objetivo")
    precio_objetivo = st.number_input("Precio objetivo (?)", value=PRECIO_OBJETIVO_DEFAULT, step=25, min_value=0)
    st.metric("Target", f"{precio_objetivo:.0f} €")
    vuelos_bajo = len(df_filtrado[df_filtrado['precio_total'] < precio_objetivo])
    if vuelos_bajo > 0:
        st.success(f"🔥 {vuelos_bajo} vuelo(s) bajo objetivo!")
    
    st.markdown("---")
    st.markdown("### 🔔 Alertas Personalizadas")
    with st.expander("Configurar Alertas"):
        alert_precio = st.number_input("Precio <", value=750, step=50, min_value=0)
        alert_duracion = st.number_input("Duración <", value=16.0, step=0.5, min_value=0.0)
        alert_score = st.slider("Score >", 0, 100, 85)
    
    alertas_config = {
        'precio_max': alert_precio,
        'duracion_max': alert_duracion,
        'score_min': alert_score
    }
    
    st.markdown("---")
    st.markdown("### 💾 Exportar")
    if st.button("📊 Descargar Excel"):
        excel_data = exportar_excel(df_filtrado)
        st.download_button(
            label="⬇️ Descargar",
            data=excel_data,
            file_name=f"bali_flights_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    st.markdown("---")
    st.caption("v4.0 Advanced Features")

if df_filtrado.empty:
    st.warning("Sin datos.")
    st.stop()

# --- ALERTAS ACTIVAS ---
alertas_list, df_con_alertas = check_alertas(df_filtrado, alertas_config)
if alertas_list:
    st.success(f"🔔 **ALERTAS ACTIVAS ({len(alertas_list)})**")
    for alerta in alertas_list:
        st.write(f"• {alerta}")
    st.markdown("---")

# --- HEADER ---
st.title("Bali Flight Tracker")
st.markdown("Monitorización en tiempo real • Precios en EUR")
st.markdown("###")

# --- KPIS ---
col1, col2, col3, col4, col5 = st.columns(5)
vuelo_barato = df_filtrado.loc[df_filtrado['precio_total'].idxmin()]
delta_objetivo = vuelo_barato['precio_total'] - precio_objetivo

col1.metric("Mejor Precio", f"{df_filtrado['precio_total'].min():.0f} €", 
            delta=f"{delta_objetivo:.0f}€ vs objetivo", 
            delta_color="inverse" if delta_objetivo < 0 else "normal")
col2.metric("Precio Medio", f"{df_filtrado['precio_total'].mean():.0f} €")
col3.metric("Aerolínea Top", vuelo_barato['nombre_aerolinea'])
col4.metric("Duración Mín.", f"{vuelo_barato['duracion_horas']:.1f} h")
col5.metric("Asientos Disp.", f"{int(vuelo_barato['asientos_disponibles'])}")

st.markdown("###")

# --- PESTAÑAS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Panorama", "✈️ Aerolíneas", "🗺️ Mapa de Rutas", "📋 Datos"])

# === TAB 1 ===
with tab1:
    st.markdown("### 🏆 Top 3 Mejores Ofertas")
    top_ofertas = obtener_top_ofertas(df_filtrado, 3)
    
    if not top_ofertas.empty:
        cols = st.columns(3)
        medallas = ["🥇", "🥈", "🥉"]
        
        for idx, (_, vuelo) in enumerate(top_ofertas.iterrows()):
            with cols[idx]:
                border = "#00AA00" if vuelo['precio_total'] < precio_objetivo else "#111111"
                st.markdown(f"""
                <div style="border: 2px solid {border}; border-radius: 10px; padding: 15px; background: #f9f9f9;">
                    <h3>{medallas[idx]} Score: {vuelo['score']}/100</h3>
                    <p style="font-size: 24px; font-weight: bold;">{vuelo['precio_total']:.0f}€</p>
                    <p>✈️ {vuelo['nombre_aerolinea']}</p>
                    <p>📅 {vuelo['fecha_salida'].strftime('%d-%b-%Y')}</p>
                    <p>⏱️ {vuelo['duracion_horas']:.1f}h | 🎫 {int(vuelo['asientos_disponibles'])}</p>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("###")
    
    # PREDICCIONES
    st.markdown("### 📊 Predicciones de Precio")
    fechas = sorted(df_filtrado['fecha_salida'].unique())[:5]
    if fechas:
        cols_pred = st.columns(min(len(fechas), 5))
        for idx, fecha in enumerate(fechas):
            with cols_pred[idx]:
                icono, cambio, rec, pred = predecir_tendencia(df_filtrado, fecha)
                precio_actual = df_filtrado[df_filtrado['fecha_salida'] == fecha]['precio_total'].iloc[-1]
                
                st.metric(f"{icono} {fecha.strftime('%d-%b')}", f"{precio_actual:.0f}€", 
                         delta=f"{cambio:+.1f}%")
                st.caption(rec)
                if pred:
                    st.caption(f"Pred 7d: {pred:.0f}€")
    
    st.markdown("###")
    st.plotly_chart(plot_calendar_heatmap(df_filtrado), use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1:
        df_dias = df_filtrado.groupby('fecha_salida')['precio_total'].min().reset_index()
        fig_bar = px.bar(df_dias, x='fecha_salida', y='precio_total')
        fig_bar.add_hline(y=precio_objetivo, line_dash="dash", line_color="red")
        fig_bar.update_layout(template='plotly_white', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with c2:
        fig_line = px.line(df_filtrado, x='fecha_consulta', y='precio_total', color='origen')
        fig_line.add_hline(y=precio_objetivo, line_dash="dash", line_color="red")
        fig_line.update_layout(template='plotly_white', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_line, use_container_width=True)

# === TAB 2 ===
with tab2:
    st.plotly_chart(crear_grafico_impuestos(df_filtrado), use_container_width=True)

# === TAB 3: MAPA ===
with tab3:
    st.markdown("### 🗺️ Rutas de Vuelo a Bali")
    st.markdown("**Verde** = Barato (<800€) | **Amarillo** = Medio (800-900€) | **Rojo** = Caro (>900€)")
    st.plotly_chart(crear_mapa_rutas(df_filtrado), use_container_width=True)

# === TAB 4 ===
with tab4:
    df_display = df_filtrado.copy()
    df_display['score'] = df_display.apply(calcular_score_vuelo, axis=1)
    df_display['🎯'] = df_display['precio_total'] < precio_objetivo
    df_display['🎯'] = df_display['🎯'].map({True: '✅', False: '❌'})
    
    # Ordenamos columnas y aplicamos configuración visual bonita
    st.dataframe(
        df_display[[
            'fecha_consulta',  # <--- NUEVO: Fecha en que el bot vio el precio
            'fecha_salida', 
            'origen', 
            'nombre_aerolinea', 
            'precio_total', 
            'duracion_horas', 
            'score', 
            '🎯'
        ]].sort_values("fecha_consulta", ascending=False), # Ordenar por lo más reciente encontrado
        use_container_width=True, 
        hide_index=True,
        column_config={
            "fecha_consulta": st.column_config.DatetimeColumn(
                "🔎 Encontrado el...",
                format="DD-MM-YYYY HH:mm", # Muestra día y hora exacta
                help="Fecha y hora en que el bot encontró este precio"
            ),
            "fecha_salida": st.column_config.DateColumn(
                "🛫 Salida Vuelo", 
                format="DD-MM-YYYY"
            ),
            "origen": "Origen",
            "nombre_aerolinea": "Aerolínea",
            "precio_total": st.column_config.NumberColumn(
                "Precio Total",
                format="%.0f €"
            ),
            "duracion_horas": st.column_config.NumberColumn(
                "Duración",
                format="%.1f h"
            ),
            "score": st.column_config.ProgressColumn(
                "Calidad", 
                min_value=0, 
                max_value=100,
                format="%.2f"
            ),
            "🎯": st.column_config.TextColumn(
                "Obj",
                help="¿Está por debajo de tu precio objetivo?"
            )
        }
    )

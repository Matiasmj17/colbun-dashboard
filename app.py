import os
import sys
import json
import sqlite3
import socket
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. CONFIGURACIÓN DE BASE DE DATOS LOCAL
# ==========================================
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "encuestas_central.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS encuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            plataforma TEXT,
            estacion TEXT,
            nota INTEGER,
            comentario TEXT,
            fecha TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def guardar_encuesta(usuario, plataforma, estacion, nota, comentario, fecha=None):
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO encuestas (usuario, plataforma, estacion, nota, comentario, fecha)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (usuario, plataforma, estacion, int(nota), comentario, fecha))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id

def leer_encuestas():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM encuestas ORDER BY id DESC", conn)
    conn.close()
    return df

def limpiar_encuestas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM encuestas")
    conn.commit()
    conn.close()

# ==========================================
# 2. SERVIDOR RECEPTOR HTTP (OFFLINE LAN)
# ==========================================
class EncuestasHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_OPTIONS(self):
        # Para peticiones pre-flight de navegadores (iOS Safari / Chrome)
        self._set_cors_headers(200)

    def do_GET(self):
        if self.path in ('/', '/ping'):
            self._set_cors_headers(200)
            res = {"status": "ok", "app": "Colbun Explorer AR Receptor", "hora": datetime.now().isoformat()}
            self.wfile.write(json.dumps(res).encode('utf-8'))
        elif self.path == '/api/encuestas':
            self._set_cors_headers(200)
            df = leer_encuestas()
            res = df.to_dict(orient='records')
            self.wfile.write(json.dumps(res).encode('utf-8'))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "No encontrado"}).encode('utf-8'))

    def do_POST(self):
        if self.path == '/api/encuesta':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len)
                data = json.loads(body.decode('utf-8'))
                
                usuario = data.get('usuario', 'Visitante Anónimo')
                plataforma = data.get('plataforma', 'Android')
                estacion = data.get('estacion', 'Estación 4 - Peces del Biobío')
                nota = int(data.get('nota', 5))
                comentario = data.get('comentario', '')
                fecha = data.get('fecha', None)
                
                nuevo_id = guardar_encuesta(usuario, plataforma, estacion, nota, comentario, fecha)
                
                self._set_cors_headers(200)
                respuesta = {
                    "status": "ok",
                    "id": nuevo_id,
                    "mensaje": "Encuesta recibida y guardada exitosamente"
                }
                self.wfile.write(json.dumps(respuesta).encode('utf-8'))
            except Exception as e:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({"status": "error", "mensaje": str(e)}).encode('utf-8'))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Ruta no valida"}).encode('utf-8'))

    def log_message(self, format, *args):
        # Silenciar logs ruidosos en consola
        return

def obtener_ips_locales():
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except:
        pass
    if not ips:
        ips.append("192.168.137.1")
    return ips

@st.cache_resource
def iniciar_servidor_segundo_plano():
    puerto = 8000
    try:
        servidor = HTTPServer(('0.0.0.0', puerto), EncuestasHandler)
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        return puerto
    except Exception as e:
        return None

PUERTO_API = iniciar_servidor_segundo_plano()
LISTA_IPS = obtener_ips_locales()
IP_PRINCIPAL = LISTA_IPS[0] if LISTA_IPS else "192.168.137.1"

# ==========================================
# 3. INTERFAZ STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Colbún Explorer AR - Métricas",
    page_icon="🦊",
    layout="wide"
)

# Estilo personalizado Colbún
st.markdown("""
<style>
    .metric-box {
        background-color: #f0f7f4;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #2d6a4f;
    }
    .badge-ip {
        background-color: #1b4332;
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Encabezado
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("🦊 Colbún Explorer AR")
    st.subheader("📊 Panel de Métricas de Satisfacción - Recorrido Sendero Túnel")
with col_h2:
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.rerun()

# Banner de estado de la red local
st.info(f"""
📡 **Servidor Receptor Offline Activo (Puerto {PUERTO_API or 8000}):**  
Los teléfonos conectados a tu Hotspot deben enviar sus encuestas a:  
👉 `http://{IP_PRINCIPAL}:{PUERTO_API or 8000}/api/encuesta`
""")

# ==========================================
# BARRA LATERAL (SIMULADOR Y CONFIGURACIÓN)
# ==========================================
with st.sidebar:
    st.header("⚙️ Herramientas de Prueba")
    
    st.write("### 🧪 Enviar encuesta de prueba")
    with st.form("form_prueba"):
        sim_usuario = st.text_input("Nombre Visitante", value="Matias Turista")
        sim_plat = st.selectbox("Plataforma", ["Android", "iOS"])
        sim_estacion = st.selectbox("Estación", [
            "Estación 1 - El Inicio",
            "Estación 2 - Sendero Pehuén",
            "Estación 3 - Flora Nativa",
            "Estación 4 - Peces del Biobío",
            "Estación 5 - Mirador Central"
        ], index=3)
        sim_nota = st.slider("Calificación (Estrellas)", 1, 5, 5)
        sim_comentario = st.text_area("Comentario", value="¡Excelente experiencia interactiva con realidad aumentada!")
        btn_sim = st.form_submit_button("Simular Envío")
        
        if btn_sim:
            guardar_encuesta(sim_usuario, sim_plat, sim_estacion, sim_nota, sim_comentario)
            st.success("¡Encuesta simulada registrada!")
            st.rerun()
            
    st.markdown("---")
    st.write("### ⚠️ Zona de Peligro")
    if st.button("🗑️ Limpiar Todas las Encuestas", type="secondary"):
        limpiar_encuestas()
        st.warning("Base de datos reiniciada a cero.")
        st.rerun()

# ==========================================
# 4. CARGA DE DATOS Y MÉTRICAS
# ==========================================
df = leer_encuestas()

if df.empty:
    st.warning("⏳ No hay encuestas registradas todavía. Las encuestas aparecerán automáticamente cuando los teléfonos presionen 'Enviar Encuesta' o cuando generes una en la barra lateral.")
else:
    # Tarjetas métricas
    total_encuestas = len(df)
    promedio_nota = df["nota"].mean()
    total_android = len(df[df["plataforma"].str.lower() == "android"])
    total_ios = len(df[df["plataforma"].str.lower() == "ios"])
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label="👥 Total Encuestados", value=total_encuestas)
    with m2:
        estrellas = "⭐" * int(round(promedio_nota))
        st.metric(label="⭐ Promedio Satisfacción", value=f"{promedio_nota:.1f} / 5.0", delta=estrellas)
    with m3:
        st.metric(label="🤖 Respuestas Android", value=total_android)
    with m4:
        st.metric(label="🍏 Respuestas iOS", value=total_ios)

    st.markdown("---")

    # Gráficos
    c_graf1, c_graf2 = st.columns(2)
    
    with c_graf1:
        st.subheader("⭐ Distribución de Calificaciones")
        distribucion = df["nota"].value_counts().reset_index()
        distribucion.columns = ["Nota", "Cantidad"]
        fig_notas = px.bar(
            distribucion,
            x="Nota",
            y="Cantidad",
            color="Nota",
            text="Cantidad",
            color_continuous_scale=["#e76f51", "#f4a261", "#e9c46a", "#2a9d8f", "#264653"],
            range_x=[0.5, 5.5]
        )
        fig_notas.update_layout(xaxis=dict(tickmode='linear', tick0=1, dtick=1), showlegend=False)
        st.plotly_chart(fig_notas, use_container_width=True)

    with c_graf2:
        st.subheader("📱 Proporción por Plataforma")
        fig_plat = px.pie(
            df,
            names="plataforma",
            color="plataforma",
            color_discrete_map={"Android": "#3DDC84", "iOS": "#A2AAAD"},
            hole=0.4
        )
        st.plotly_chart(fig_plat, use_container_width=True)

    st.markdown("---")
    
    # Tabla detallada y comentarios
    st.subheader("📋 Registro Detallado de Respuestas en Vivo")
    st.dataframe(
        df[["id", "fecha", "usuario", "plataforma", "estacion", "nota", "comentario"]],
        use_container_width=True,
        hide_index=True
    )

    # Descarga
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Informe Completo (CSV / Excel)",
        data=csv_bytes,
        file_name=f"informe_encuestas_colbun_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

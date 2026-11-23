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

# ==========================================
# 1. BASE DE DATOS LOCAL PARA STREAMLIT
# ==========================================
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "encuestas_central.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS encuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_sesion TEXT,
            origen TEXT,
            edad TEXT,
            nota INTEGER,
            comentario TEXT,
            fecha TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def guardar_encuesta(id_sesion, origen, edad, nota, comentario, fecha=None):
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO encuestas (id_sesion, origen, edad, nota, comentario, fecha)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (id_sesion, origen, edad, int(nota), comentario, fecha))
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
# 2. SERVIDOR RECEPTOR OFFLINE (PUERTO 8000)
# ==========================================
class EncuestasHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        if self.path in ('/', '/ping'):
            self._set_headers(200)
            res = {"status": "ok", "app": "Colbun Explorer AR Receptor", "hora": datetime.now().isoformat()}
            self.wfile.write(json.dumps(res).encode('utf-8'))
        elif self.path == '/api/encuestas':
            self._set_headers(200)
            df = leer_encuestas()
            self.wfile.write(json.dumps(df.to_dict(orient='records')).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "No encontrado"}).encode('utf-8'))

    def do_POST(self):
        if self.path == '/api/encuesta':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len)
                data = json.loads(body.decode('utf-8'))
                
                id_sesion = data.get('id_sesion', 'anonimo')
                origen = data.get('origen', 'Santa Bárbara')
                edad = data.get('edad', '18 a 29')
                nota = int(data.get('nota', 5))
                comentario = data.get('comentario', '')
                fecha = data.get('fecha', None)
                
                nuevo_id = guardar_encuesta(id_sesion, origen, edad, nota, comentario, fecha)
                
                self._set_headers(200)
                respuesta = {
                    "status": "ok",
                    "id": nuevo_id,
                    "mensaje": "Encuesta de la app Android registrada con éxito"
                }
                self.wfile.write(json.dumps(respuesta).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"status": "error", "mensaje": str(e)}).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Ruta no valida"}).encode('utf-8'))

    def log_message(self, format, *args):
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
    except:
        return None

PUERTO_API = iniciar_servidor_segundo_plano()
LISTA_IPS = obtener_ips_locales()
IP_PRINCIPAL = LISTA_IPS[0] if LISTA_IPS else "192.168.137.1"

# ==========================================
# 3. INTERFAZ STREAMLIT (COLBÚN EXPLORER AR)
# ==========================================
st.set_page_config(
    page_title="Colbún Explorer AR - Panel de Encuestas",
    page_icon="🦊",
    layout="wide"
)

# Encabezado
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("🦊 Colbún Explorer AR")
    st.subheader("📊 Métricas de Encuestas de Visitantes (App Android)")
with col_h2:
    if st.button("🔄 Actualizar Datos", width='stretch'):
        st.rerun()

# Banner de conexión local
st.info(f"""
📡 **Receptor Offline Activo en Puerto {PUERTO_API or 8000}**  
Conecta tu celular a la **Zona cubierta móvil** de la laptop.  
Tu aplicación en Android enviará automáticamente las encuestas a: `http://{IP_PRINCIPAL}:{PUERTO_API or 8000}/api/encuesta`
""")

# Barra Lateral con Simulador y Herramientas
with st.sidebar:
    st.header("⚙️ Herramientas")
    
    st.write("### 🧪 Probar envío manual")
    with st.form("form_prueba"):
        sim_origen = st.selectbox("Origen", ["Santa Bárbara", "Quilaco", "Los Ángeles", "Otra comuna del Biobío", "Otra región de Chile", "Otro país"])
        sim_edad = st.selectbox("Rango de Edad", ["Menor de 18", "18 a 29", "30 a 59", "60 o más"], index=1)
        sim_nota = st.slider("Calificación (Estrellas)", 1, 5, 5)
        sim_comentario = st.text_area("Comentario del Visitante", value="¡Los modelos de peces en realidad aumentada están geniales!")
        btn_sim = st.form_submit_button("Simular Encuesta")
        
        if btn_sim:
            guardar_encuesta("prueba_manual", sim_origen, sim_edad, sim_nota, sim_comentario)
            st.success("¡Encuesta registrada exitosamente!")
            st.rerun()

    st.markdown("---")
    st.write("### ⚠️ Reiniciar Base de Datos")
    if st.button("🗑️ Limpiar Encuestas"):
        limpiar_encuestas()
        st.warning("Base de datos reiniciada a cero.")
        st.rerun()

# ==========================================
# 4. DASHBOARD Y VISUALIZACIÓN DE MÉTRICAS
# ==========================================
df = leer_encuestas()

if df.empty:
    st.warning("⏳ Esperando respuestas desde la app móvil. Responde la encuesta en la aplicación de Unity o usa el botón de prueba en la barra lateral.")
else:
    total_encuestas = len(df)
    promedio_nota = df["nota"].mean()
    comuna_top = df["origen"].mode()[0] if not df["origen"].empty else "N/A"
    edad_top = df["edad"].mode()[0] if not df["edad"].empty else "N/A"
    
    # Tarjetas métricas
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label="👥 Total Encuestados", value=total_encuestas)
    with m2:
        estrellas = "⭐" * int(round(promedio_nota))
        st.metric(label="⭐ Satisfacción Promedio", value=f"{promedio_nota:.1f} / 5.0", delta=estrellas)
    with m3:
        st.metric(label="📍 Comuna / Origen Frecuente", value=comuna_top)
    with m4:
        st.metric(label="🎂 Grupo Etario Principal", value=edad_top)

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
        st.plotly_chart(fig_notas, width='stretch')

    with c_graf2:
        st.subheader("📍 Procedencia de los Visitantes")
        fig_origen = px.pie(
            df,
            names="origen",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4
        )
        st.plotly_chart(fig_origen, width='stretch')

    c_graf3, c_graf4 = st.columns(2)
    with c_graf3:
        st.subheader("🎂 Rangos de Edad de Visitantes")
        fig_edad = px.bar(
            df["edad"].value_counts().reset_index(),
            x="edad",
            y="count",
            color="edad",
            labels={"edad": "Rango de Edad", "count": "Cantidad"},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_edad, width='stretch')

    with c_graf4:
        st.subheader("💬 Últimos Comentarios Recibidos")
        comentarios_recientes = df[df["comentario"].str.strip() != ""]["comentario"].head(4)
        if comentarios_recientes.empty:
            st.info("Aún no hay comentarios de texto escritos.")
        else:
            for com in comentarios_recientes:
                st.markdown(f"> 💬 *\"{com}\"*")

    st.markdown("---")

    # Tabla en vivo
    st.subheader("📋 Registro Detallado de Respuestas")
    st.dataframe(
        df[["id", "fecha", "origen", "edad", "nota", "comentario"]],
        width='stretch',
        hide_index=True
    )

    # Botón para descargar informe en CSV
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Informe Completo (CSV)",
        data=csv_bytes,
        file_name=f"informe_encuestas_colbun_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

# 🦊 Colbún Explorer AR - Panel de Métricas & Servidor Receptor Offline

Sistema de consolidación y visualización de encuestas en tiempo real para el recorrido patrimonial del Túnel del Agua (Parque Angostura / Colbún).

Diseñado para funcionar **100% offline** mediante la **Zona con cobertura móvil (Hotspot)** de la laptop, recibiendo datos de:
- 🤖 **Android:** Aplicación nativa en Unity (Vuforia AR).
- 🍏 **iOS:** Aplicación / formulario web en HTML5 / JavaScript.

---

## 🚀 Cómo Ejecutar en la Laptop
1. Activa la **Zona con cobertura móvil** (Mobile Hotspot) en Windows.
2. Conecta los teléfonos a esa red Wi-Fi.
3. Haz doble clic en `iniciar_dashboard.bat` (o ejecuta `streamlit run app.py`).
4. Se abrirá automáticamente el panel en tu navegador.

---

## 📡 Endpoint de la API Offline
- **URL:** `http://<IP_DE_TU_LAPTOP>:8000/api/encuesta`
- **Método:** `POST`
- **Headers:** `Content-Type: application/json`
- **CORS:** Habilitado (`*`) para navegadores Safari y Chrome.

### Estructura JSON:
```json
{
  "usuario": "Turista 1",
  "plataforma": "iOS",
  "estacion": "Estación 4 - Peces del Biobío",
  "nota": 5,
  "comentario": "Excelente experiencia AR",
  "fecha": "2026-11-23 20:00:00"
}
```

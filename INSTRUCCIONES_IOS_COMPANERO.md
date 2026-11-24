# 🍏 Guía para la Integración de Encuestas iOS (Web) -> Servidor Streamlit

Este documento contiene la especificación exacta para que la inteligencia artificial de tu compañero agregue el envío de encuestas desde la aplicación web de iOS hacia la laptop (Servidor Streamlit).

---

## 🎯 Objetivo
Cuando el visitante en iOS complete el formulario de encuesta y presione **"Enviar"**, la página web debe enviar un `POST` en formato JSON por la red local (Wi-Fi) hacia la laptop que tiene abierto el dashboard.

---

## 📡 Especificación del Endpoint (API Local)
- **URL por defecto:** `http://192.168.137.1:8000/api/encuesta` *(o la IP que muestre la laptop en el panel de Streamlit)*
- **Método HTTP:** `POST`
- **Headers:** `Content-Type: application/json`
- **CORS:** Ya está habilitado con `*` en el servidor para Safari / Chrome.

### 📄 Formato del JSON a enviar:
```json
{
  "id_sesion": "ios_anonimo_12345",
  "origen": "Santa Bárbara",
  "edad": "18 a 29",
  "nota": 5,
  "comentario": "Los modelos de realidad aumentada se ven increíbles.",
  "fecha": "2026-11-23 21:00:00"
}
```

### 📋 Campos requeridos y valores estándar:
| Campo | Tipo | Valores permitidos / Formato |
|---|---|---|
| `id_sesion` | string | Identificador único anónimo (ej: `ios_` + timestamp o UUID) |
| `origen` | string | `"Santa Bárbara"`, `"Quilaco"`, `"Los Ángeles"`, `"Otra comuna del Biobío"`, `"Otra región de Chile"`, `"Otro país"` |
| `edad` | string | `"Menor de 18"`, `"18 a 29"`, `"30 a 59"`, `"60 o más"` |
| `nota` | integer | Número entero del `1` al `5` (calificación con estrellas) |
| `comentario` | string | Texto libre con la opinión del visitante (puede ser vacío `""`) |
| `fecha` | string | Formato `"YYYY-MM-DD HH:mm:ss"` |

---

## 💻 Código JavaScript listo para copiar y pegar:

```javascript
// Función para enviar la encuesta a la laptop por red local
async function enviarEncuestaServidor(datosEncuesta, ipLaptop = "192.168.137.1") {
    const url = `http://${ipLaptop}:8000/api/encuesta`;

    const payload = {
        id_sesion: datosEncuesta.id_sesion || ("ios_" + Date.now()),
        origen: datosEncuesta.origen,         // Ej: "Santa Bárbara"
        edad: datosEncuesta.edad,             // Ej: "18 a 29"
        nota: parseInt(datosEncuesta.nota),   // 1 al 5
        comentario: datosEncuesta.comentario || "",
        fecha: new Date().toISOString().replace('T', ' ').substring(0, 19)
    };

    try {
        const respuesta = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (respuesta.ok) {
            const resultado = await respuesta.json();
            console.log("✅ Encuesta guardada en el Dashboard central:", resultado);
            return { exito: true };
        } else {
            throw new Error("Error en servidor: " + respuesta.status);
        }
    } catch (error) {
        console.warn("⚠️ No se pudo enviar a la laptop (modo offline). Guardando en localStorage:", error.message);
        
        // Respaldo offline en el navegador del iPhone por si se desconecta el Wi-Fi
        const guardadas = JSON.parse(localStorage.getItem('encuestas_pendientes') || '[]');
        guardadas.push(payload);
        localStorage.setItem('encuestas_pendientes', JSON.stringify(guardadas));

        return { exito: false, guardadoLocal: true };
    }
}
```

---

## 🛠️ Cómo Probarlo
1. Conectar el iPhone a la misma red Wi-Fi de la laptop.
2. Completar la encuesta en la web de iOS y presionar Enviar.
3. El panel de Streamlit en la laptop sumará automáticamente la respuesta al contador y a los gráficos de torta y barras.

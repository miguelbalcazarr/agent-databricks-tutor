# Tutor de Certificaciones (agent-databricks-tutor)

Practicá para tus exámenes de certificación con preguntas tipo examen,
fundamentadas en la documentación oficial de cada proveedor, no
inventadas. Elegí una certificación, respondé en modo **Práctica** (una
pregunta a la vez, con feedback inmediato) o date un **Simulacro**
cronometrado igual al examen real, y seguí tu progreso entre sesiones.

Certificaciones disponibles hoy:

- **Databricks Certified Data Engineer Associate**
- **Microsoft Certified: Fabric Data Engineer Associate (DP-700)**

Ver [CHANGELOG.md](CHANGELOG.md) para las últimas novedades.

## Cómo correrlo

Requiere **Python 3.11 o superior** y `git`.

```bash
git clone https://github.com/miguelbalcazarr/agent-databricks-tutor.git
cd agent-databricks-tutor

python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run frontend/streamlit_app.py
```

Se abre solo en tu navegador en `http://localhost:8501`. Si no se abre
solo, entrá a esa dirección manualmente.

**No hace falta ninguna API key ni archivo `.env` para usar el Quiz.**
Responder preguntas, ver resultados y guardar tu progreso funciona 100%
local, sin conexión a ningún LLM. Tu progreso se guarda en un SQLite
local dentro de `data/progress/`, separado del banco de preguntas.

La única función opcional que necesita configuración (y que no hace falta
para practicar) es el envío del informe del Simulacro por correo. Si no
la configurás, el Quiz funciona igual, solo que no llega ese correo
extra.

## Para Miguel (generación de preguntas nuevas)

La generación de preguntas (offline, con LLM) es un proceso aparte que no
corre el alumno. Ver `docs/contexto/arquitectura.md` y
`docs/contexto/decisiones.md` para el detalle completo del stack, las
decisiones de diseño, y cómo correr `tools/generate_questions.py`.

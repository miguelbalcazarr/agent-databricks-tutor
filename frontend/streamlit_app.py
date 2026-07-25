import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frontend.home import certification_home_entries, make_home_page
from frontend.quiz_page import make_quiz_page
from tools.certifications import load_registry

st.set_page_config(page_title="Tutor de Certificaciones", layout="wide")

certifications = load_registry()
quiz_pages = {cert.slug: make_quiz_page(cert) for cert in certifications}

# Cada familia de agentes aporta sus propias HomeEntry + paginas. Hoy solo
# hay tutores de certificacion; un agente con logica distinta se suma como
# otra fuente de entries + paginas aca, sin tocar frontend/home.py — ver
# docs/contexto/decisiones.md D19.
home_entries = certification_home_entries(certifications, quiz_pages)
all_pages = list(quiz_pages.values())

home_page = make_home_page(home_entries)

st.navigation([home_page] + all_pages).run()

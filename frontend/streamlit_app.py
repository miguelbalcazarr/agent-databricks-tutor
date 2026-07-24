import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frontend.home import make_home_page
from frontend.quiz_page import make_quiz_page
from tools.certifications import load_registry

st.set_page_config(page_title="Tutor de Certificaciones", layout="wide")

certifications = load_registry()
quiz_pages = {cert.slug: make_quiz_page(cert) for cert in certifications}
home_page = make_home_page(certifications, quiz_pages)

st.navigation([home_page] + list(quiz_pages.values())).run()

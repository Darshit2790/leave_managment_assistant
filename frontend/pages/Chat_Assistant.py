import streamlit as st
import uuid
import sys

from pathlib import Path


from pathlib import Path
import streamlit as st

css_path = (
    Path(__file__).resolve().parent
    / "assets"
    / "style.css"
)

if not css_path.exists():
    css_path = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "style.css"
    )

if css_path.exists():

    with open(css_path, encoding="utf-8") as file:

        st.markdown(
            f"<style>{file.read()}</style>",
            unsafe_allow_html=True
        )


# Add project root to Python path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from components.sidebar import render_sidebar
from components.chat_ui import render_chat_ui


# -------------------------------
# Page Configuration
# -------------------------------

st.set_page_config(
    page_title="AI Leave Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -------------------------------
# Session Initialization
# -------------------------------

if "messages" not in st.session_state:

    st.session_state.messages = []


if "session_id" not in st.session_state:

    st.session_state.session_id = str(uuid.uuid4())


if "employee_id" not in st.session_state:

    st.session_state.employee_id = "EMP001"


# -------------------------------
# Sidebar
# -------------------------------

render_sidebar()


# -------------------------------
# Main Chat Interface
# -------------------------------

render_chat_ui()
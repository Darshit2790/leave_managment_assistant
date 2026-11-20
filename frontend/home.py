import streamlit as st

from components.sidebar import render_sidebar

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


st.set_page_config(
    page_title="HR Assistant Dashboard",
    page_icon="🏢",
    layout="wide"
)

render_sidebar()

st.title("🏢 Employee HR Dashboard")

st.caption(
    "Welcome to your AI-powered HR Management Assistant."
)

st.divider()

# Dashboard metrics

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Annual Leaves",
        "18",
        "Available allocation"
    )

with col2:

    st.metric(
        "Casual Leaves",
        "7",
        "Available allocation"
    )

with col3:

    st.metric(
        "Pending Requests",
        "2",
        "Awaiting approval"
    )

st.divider()

st.subheader("🚀 Quick Actions")

col1, col2 = st.columns(2)

with col1:

    st.info(
        "🤖 **AI HR Assistant**\n\n"
        "Ask questions about HR policies and "
        "employee information."
    )

    if st.button(
        "Open AI Assistant",
        use_container_width=True
    ):

        st.switch_page(
            "pages/1_Chat_Assistant.py"
        )

with col2:

    st.info(
        "📝 **Apply for Leave**\n\n"
        "Submit a new leave application "
        "through the HR assistant."
    )

    if st.button(
        "Apply Leave",
        use_container_width=True
    ):

        st.switch_page(
            "pages/3_Apply_Leave.py"
        )
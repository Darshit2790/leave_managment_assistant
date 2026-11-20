import streamlit as st


def render_sidebar():

    with st.sidebar:

        st.title("🤖 HR Assistant")

        st.caption("AI-powered employee support")

        st.divider()

        st.subheader("Employee Profile")

        employee_id = st.text_input(
            "Employee ID",
            value=st.session_state.get(
                "employee_id",
                "EMP001"
            )
        )

        st.session_state.employee_id = employee_id

        st.divider()

        st.subheader("Navigation")

        #st.page_link(
         #   "Home.py",
          #  label="Home",
           # icon="🏠"
        #)

        st.page_link(
            "pages/chat_assistant.py",
            label="AI Assistant",
            icon="🤖"
        )

        st.page_link(
            "pages/leave_balance.py",
            label="Leave Balance",
            icon="📊"
        )

        st.page_link(
            "pages/apply_leave.py",
            label="Apply Leave",
            icon="📝"
        )

        st.page_link(
            "pages/leave_history.py",
            label="Leave History",
            icon="📅"
        )

        st.divider()

        st.subheader("Conversation")

        if st.button(
            "＋ New Conversation",
            use_container_width=True
        ):

            st.session_state.messages = []
            st.session_state.pending_action = None

            import uuid

            st.session_state.session_id = str(
                uuid.uuid4()
            )

            st.rerun()

        st.caption("Powered by RAG + Agentic AI")
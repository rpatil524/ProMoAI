
import streamlit as st
from promoai.general_utils.ai_providers import (
    AI_HELP_DEFAULTS,
    AI_MODEL_DEFAULTS,
    DEFAULT_AI_PROVIDER,
    MAIN_HELP,
)

from promoai.general_utils.llm_connection import LLMConnection


def run_page():
    # Initialize State
    if "provider" not in st.session_state:
        st.session_state["provider"] = list(AI_MODEL_DEFAULTS.keys())[0]
    if "model_name" not in st.session_state:
        st.session_state["model_name"] = AI_MODEL_DEFAULTS[st.session_state["provider"]]

    def on_provider_change():
        st.session_state["model_name"] = AI_MODEL_DEFAULTS[st.session_state["provider"]]

    # UI Elements
    st.write("### 🔑 API Configuration")
    
    with st.container(border=True):
        provider = st.selectbox(
            "AI Provider",
            options=AI_MODEL_DEFAULTS.keys(),
            key="provider",
            on_change=on_provider_change,
            help=MAIN_HELP
        )

        col1, col2 = st.columns(2)
        with col1:
            ai_model_name = st.text_input(
                "Model Name",
                key="model_name",
                help=AI_HELP_DEFAULTS.get(st.session_state["provider"], "")
            )
        with col2:
            api_key = st.text_input("API Key", type="password", placeholder="my-precious-api-key")

        if st.button("Save Credentials", type="primary", use_container_width=True):
            if not api_key:
                st.error("Please enter an API key.")
            else:
                st.session_state["llm_credentials"] = LLMConnection(
                    api_key=api_key, 
                    llm_name=ai_model_name, 
                    ai_provider=provider
                )
                st.success("Credentials saved! You can now navigate to ProMoAI or PMAx.")
    st.markdown("<br>", unsafe_allow_html=True) # Adds some breathing room
    st.divider()
    
    # Single line: Name [Email Icon] [LinkedIn Icon]
    st.caption(
        "Humam Kourani [✉️](mailto:humam.kourani@fit.fraunhofer.de) [🔗](https://www.linkedin.com/in/humam-kourani-98b342232) • "
        "Alessandro Berti [✉️](mailto:a.berti@pads.rwth-aachen.de) [🔗](https://www.linkedin.com/in/dr-alessandro-berti-2a483766) • "
        "Anton Antonov [✉️](mailto:anton.antonov@fit.fraunhofer.de) [🔗](https://www.linkedin.com/in/anton-antonov-5448291a6) • "
    )
    st.caption(
        "ProMoAI is developed at the Fraunhofer Institute for Applied Information Technology FIT. "
    )
if __name__ in {"__main__", "__page__"}:
    run_page()


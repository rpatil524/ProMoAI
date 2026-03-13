import os

import shutil
import tempfile
from typing import Dict, List, Union

import pandas as pd
import streamlit as st
from powl import import_event_log
from promoai.agents.agents import analyst_node, engineer_node, init_state
from promoai.general_utils.app_utils import DISCOVERY_HELP

from promoai.general_utils.llm_connection import LLMConnection
from promoai.general_utils.constants import temp_dir

from xhtml2pdf import pisa
from io import BytesIO
import base64
import base64
import os
import pandas as pd
from io import BytesIO
from xhtml2pdf import pisa
import markdown

def export_messages_to_pdf(messages) -> bytes:
    html_content = f"""
    <html>
    <head>
        <style>
            @page {{ size: a4; margin: 1cm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.5; }}
            .user {{ color: #2e77d0; font-weight: bold; margin-top: 15px; border-bottom: 1px solid #2e77d0; }}
            .assistant {{ color: #e63946; font-weight: bold; margin-top: 15px; border-bottom: 1px solid #e63946; }}
            .text {{ margin-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
            th, td {{ border: 1px solid #ccc; padding: 4px; text-align: left; font-size: 8pt; }}
            th {{ background-color: #f2f2f2; }}
            img {{ max-width: 100%; height: auto; display: block; margin: 10px auto; }}
        </style>
    </head>
    <body>
        <h1 style="text-align: center;">PMAx Analysis Report</h1>
    """

    for msg in messages:
        role_label = "User" if msg["role"] == "user" else "PMAx"
        html_content += f"<div class='{msg['role']}'>{role_label}</div>"

        blocks = msg["content"]
        if not isinstance(blocks, list):
            blocks = [{"type": "text", "content": blocks}]

        for block in blocks:
            b_type = block.get("type")
            b_val = block.get("content")

            if b_type == "text":
                # Use markdown library for cleaner HTML (faster for the PDF engine)
                clean_text = markdown.markdown(b_val)
                html_content += f"<div class='text'>{clean_text}</div>"
            
            elif b_type == "artifact":
                if os.path.exists(b_val):
                    if b_val.lower().endswith(('.png', '.jpg', '.jpeg')):
                        # INSTEAD OF BASE64: Use absolute file path
                        abs_path = os.path.abspath(b_val)
                        html_content += f"<div class='text'><img src='{abs_path}'></div>"
                    
                    elif b_val.lower().endswith('.csv'):
                        df = pd.read_csv(b_val)
                        # LIMIT ROWS: PDF tables shouldn't be 1000 rows long
                        if len(df) > 30:
                            html_content += "<p><i>(Showing first 30 rows of data)</i></p>"
                            df = df.head(30)
                        html_content += df.to_html(index=False)

    html_content += "</body></html>"

    pdf_buffer = BytesIO()
    # xhtml2pdf works better with file paths if we provide a path helper
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    
    return None if pisa_status.err else pdf_buffer.getvalue()
def display_chat_message(role: str, content: Union[str, List[Dict[str, str]]]):
    """Renders either a simple string or a structured artifact report."""
    with st.chat_message(role):
        if isinstance(content, list):
            # Loop through the list of blocks
            for block in content:
                b_type = block.get("type")
                b_val = block.get("content")

                if b_type == "text":
                    st.markdown(b_val)

                elif b_type == "artifact":
                    st.markdown(f"**Artifact:**")
                    if not os.path.exists(b_val):
                        st.error(f"File missing: {b_val}")
                        continue

                    # Logic for Images vs Dataframes
                    if b_val.lower().endswith((".png", ".jpg", ".jpeg", ".svg")):
                        st.image(b_val, use_container_width=True)
                    elif b_val.lower().endswith(".csv"):
                        df = pd.read_csv(b_val)
                        # show only the first 30 rows
                        if len(df) > 30:
                            st.markdown("<p><i>(Showing first 30 rows of data)</i></p>", unsafe_allow_html=True)
                            df = df.head(30)
                        st.dataframe(df, use_container_width=True)
                    elif b_val.lower().endswith(".parquet"):
                        df = pd.read_parquet(b_val)
                        # show only the first 30 rows
                        if len(df) > 30:
                            st.markdown("<p><i>(Showing first 30 rows of data)</i></p>", unsafe_allow_html=True)
                            df = df.head(30)
                        st.dataframe(df, use_container_width=True)
        else:
            st.markdown(content)


def chat(llm_credentials: LLMConnection):
    for message in st.session_state.messages:
        display_chat_message(message["role"], message["content"])

    if prompt := st.chat_input("Enter your message here..."):
        display_chat_message("user", prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Add user message to chat history
        if "agent_state" not in st.session_state:
            st.session_state.agent_state = init_state(
                user_request=prompt, event_log=st.session_state["uploaded_log"]
            )
        else:
            # Add the user request to the agent state
            st.session_state.agent_state["user_request"].append(prompt)
        with st.status(
            "I am processing your request...", state="running", expanded=True
        ) as status:
            status.update(
                label="The engineer is analyzing the request and preparing code...",
                state="running",
                expanded=True,
            )
            st.session_state.agent_state, _, code = engineer_node(
                st.session_state.agent_state, llm_credentials
            )
            st.write("Code generated! Executing the code and generating the report...")
            st.write(f"Executing the following code:\n```python\n{code}\n```")
            # Add the generated code to the status
            status.update(
                label="The analyst is generating the report based on the generated code and the analysis artifacts...",
                state="running",
            )
            updated_state = analyst_node(st.session_state.agent_state, llm_credentials)
            st.session_state.agent_state = updated_state
            status.update(label="Report Generated! ✅", state="complete", expanded=False)

        report = st.session_state.agent_state["final_report"]
        display_chat_message("assistant", report)
        st.session_state.messages.append({"role": "assistant", "content": report})


def run_page():
    st.title("🤖 PMAx")

    st.subheader("Your Process Mining Expert Agent")

    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "assistant", "content": "Hey! I am PMAx. How can I help you today?"}
        ]
    

    os.makedirs(temp_dir, exist_ok=True)

    if "setup_complete" not in st.session_state:
        st.session_state["setup_complete"] = False

    if st.session_state["setup_complete"]:
        if st.sidebar.button("🔄 Reset History"):
            st.session_state["setup_complete"] = False
            if "uploaded_log" in st.session_state:
                del st.session_state["uploaded_log"]
            if "agent_state" in st.session_state:
                del st.session_state["agent_state"]
            if "messages" in st.session_state:
                del st.session_state["messages"]
            st.rerun()
        if st.sidebar.button("Build PDF Report"):
            pdf_bytes = None
            if st.session_state.messages:
                with st.spinner("Converting chat and artifacts to PDF..."):
                    pdf_bytes = export_messages_to_pdf(st.session_state.messages)
                    if pdf_bytes:
                        st.sidebar.success("Successfully built PDF report!")
                    else:
                        st.sidebar.error("Error: Failed to generate PDF report.")
            else:
                st.sidebar.warning("No messages to export.")
            
            if pdf_bytes:
                st.sidebar.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name="pmax_analysis_report.pdf",
                    mime="application/pdf"
            )



    if not st.session_state["setup_complete"]:
        st.header("🔧 Agents Setup")

        with st.form(key="model_gen_form"):
            uploaded_log = st.file_uploader(
                "For **using an agent**, upload an event log:",
                type=["xes", "gz"],
                help=DISCOVERY_HELP,
            )
            submission_button = st.form_submit_button(label="Start Analysis 🚀")
            if submission_button:
                if "llm_credentials" not in st.session_state:
                    st.error(body="Please complete the setup on the main page!", icon="⚠️")
                    return
                if uploaded_log is None:
                    st.error(body="No file is selected!", icon="⚠️")
                    return
                try:
                    with st.spinner("Uploading and processing the event log..."):
                        contents = uploaded_log.read()
                        os.makedirs(temp_dir, exist_ok=True)
                        with tempfile.NamedTemporaryFile(
                            mode="wb",
                            delete=False,
                            dir=temp_dir,
                            suffix=uploaded_log.name,
                        ) as temp_file:
                            temp_file.write(contents)
                            log = import_event_log(temp_file.name)
                            if "uploaded_log" not in st.session_state:
                                st.session_state["uploaded_log"] = log
                                st.session_state["setup_complete"] = True

                                st.rerun()
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    st.error(body=f"Error : {e}", icon="⚠️")
                    return

    else:
        if "llm_credentials" not in st.session_state:
            st.error(
                body="LLM credentials are missing! Please go back to the settings and enter your credentials.",
                icon="⚠️",
            )
            return
        chat(st.session_state["llm_credentials"])


if __name__ in {"__main__", "__page__"}:
    os.environ["MPLBACKEND"] = "Agg"
    run_page()

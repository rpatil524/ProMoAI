import subprocess
import sys
from pathlib import Path
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx


def _launch_via_streamlit() -> None:
    script_path = Path(__file__).resolve()
    result = subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(script_path)],
        check=False,
    )
    raise SystemExit(result.returncode)


def run_app():
    pg = st.navigation([
        st.Page("setup_page.py", title="Setup", icon=":material/settings_suggest:", default=True),
        st.Page("promoai_page.py", title="ProMoAI", icon=":material/account_tree:"),
        st.Page("pmax.py", title="PMAx", icon=":material/query_stats:"),
    ])
    pg.run()


def apply_custom_style():
    st.markdown(
        """
        <style>
        
        .sidebar-bottom {
            margin-top: auto;
        }

        .sidebar-card {
            position: sticky;
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128,128,128,0.2);
            border-radius: 10px;
            padding: 10px 12px;
            width: 100%;
            margin-bottom: 8px;
            transition: transform 0.1s ease, border-color 0.2s;
        }

        .sidebar-card:hover {
            border-color: var(--primary-color);
            transform: translateY(-1px);
        }

        .sidebar-link {
            text-decoration: none !important;
            color: var(--text-color) !important;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .card-text-main {
            font-size: 0.8rem;
            font-weight: 600;
            display: block;
        }

        .card-text-sub {
            font-size: 0.7rem;
            opacity: 0.6;
            display: block;
        }

        .sidebar-header {
            font-size: 0.65rem;
            font-weight: 700;
            color: var(--primary-color);
            text-transform: uppercase;
            letter-spacing: 0.08rem;
            margin: 1rem 0 0.4rem 0.3rem;
        }

        /* Fraunhofer badge with wider layout */
        .branding-badge {
            background-color: white;
            padding: 10px 8px;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-decoration: none !important;
            border: 1px solid #eee;
            transition: all 0.3s ease;
            margin-top: 6px;
        }

        .branding-badge img {
            width: 140px;
        }

        .branding-text {
            color: #333 !important;
            font-size: 0.62rem;
            font-weight: 500;
            line-height: 1.3;
            margin-top: 8px;
            text-align: center;
        }

        footer {visibility: hidden;}

        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_info():
    apply_custom_style()

    with st.sidebar:

        # ---------- RESOURCES (TOP) ----------
        st.markdown("<div class='sidebar-header'>Resources</div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="sidebar-card">
                <a class="sidebar-link" href="https://doi.org/10.24963/ijcai.2024/1014" target="_blank">
                    <span style="font-size:1.2rem;">📄</span>
                    <div>
                        <span class="card-text-main">ProMoAI Paper</span>
                        <span class="card-text-sub">IJCAI 2024</span>
                    </div>
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="sidebar-card" style="opacity:0.7;">
                <a class="sidebar-link" href="#" style="cursor: default;">
                    <span style="font-size:1.2rem;">📄</span>
                    <div>
                        <span class="card-text-main">PMAx Paper</span>
                        <span class="card-text-sub">Coming Soon</span>
                    </div>
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """

            <div class='sidebar-header'>Support</div>

            <div class="sidebar-card">
                <a class="sidebar-link" href="mailto:humam.kourani@fit.fraunhofer.de;a.berti@pads.rwth-aachen.de;anton.antonov@fit.fraunhofer.de?subject=ProMoAI Inquiry">
                    <span style="font-size:1.2rem;">✉️</span>
                    <div>
                        <span class="card-text-main">Contact Developers</span>
                    </div>
                </a>
            </div>

            <div class='sidebar-header'>Developed at</div>

            <a href="https://www.fit.fraunhofer.de/" target="_blank" class="branding-badge">
                <img src="https://www.fit.fraunhofer.de/content/dam/fit/fit.svg">
                <div class="branding-text">
                    Fraunhofer Institute for Applied<br>Information Technology FIT
                </div>
            </a>

            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    if get_script_run_ctx() is None:
        _launch_via_streamlit()

    st.set_page_config(
        page_title="ProMoAI",
        page_icon="🤖",
        layout="wide"
    )

    sidebar_info()
    run_app()
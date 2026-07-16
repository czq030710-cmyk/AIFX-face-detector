import os
import base64
import json
from html import escape
from io import BytesIO
from urllib.parse import urlencode

from PIL import Image, ImageDraw
import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
AIFX_FRONTEND_URL = os.getenv("AIFX_FRONTEND_URL", "http://127.0.0.1:8501")
LOCAL_API_SESSION = requests.Session()
LOCAL_API_SESSION.trust_env = False
BEST_DETECTION_RANGE = "balanced"
BEST_DETECTION_LABEL = "Balanced recall"
CONTROL_DEFAULTS_VERSION = 5
DEFAULT_FULL_RANGE_CONFIDENCE = 0.10
DEFAULT_SHORT_RANGE_CONFIDENCE = 0.23
DEFAULT_SUPPRESSION_THRESHOLD = 0.30


def api_get(path, **kwargs):
    return LOCAL_API_SESSION.get(f"{API_URL}{path}", **kwargs)


def api_post(path, **kwargs):
    return LOCAL_API_SESSION.post(f"{API_URL}{path}", **kwargs)


st.set_page_config(page_title="AIFX Face Processing", layout="wide")
st.markdown(
    """
    <style>
    :root {
        color-scheme: dark;
    }
    html {
        color-scheme: dark;
        background: #07080D;
    }
    body {
        overflow-x: hidden;
        background: #07080D;
    }
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stDecoration"] {
        display: none;
    }
    [data-testid="stSidebar"] {
        background: #0B0D13;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p {
        color: #F4F6FA;
    }
    .account-panel {
        border: 1px solid #30343D;
        border-radius: 8px;
        padding: 14px 14px 12px;
        margin: 8px 0 14px;
        background: #171A21;
    }
    .account-kicker {
        color: #9DA3AE;
        font-size: 0.78rem;
        margin-bottom: 4px;
    }
    .account-title {
        color: #F6F8FB;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 6px;
    }
    .account-copy {
        color: #B7BDC8;
        font-size: 0.86rem;
        line-height: 1.35;
    }
    .mode-pill {
        display: inline-block;
        color: #101318;
        background: #8BE9C5;
        border-radius: 999px;
        padding: 3px 8px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-top: 8px;
    }
    .mode-pill.local {
        background: #FFD166;
    }
    .login-copy,
    .login-panel {
        position: relative;
        z-index: 1;
    }
    .login-kicker {
        display: inline-flex;
        align-items: center;
        gap: 9px;
        color: #C7D2FF;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.055);
        border-radius: 999px;
        padding: 8px 12px;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 22px;
        backdrop-filter: blur(18px);
    }
    .login-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: #8BE9C5;
        box-shadow: 0 0 22px rgba(139, 233, 197, 0.75);
    }
    .login-headline {
        color: #FFFFFF;
        font-size: clamp(3.2rem, 9vw, 7rem);
        line-height: 0.92;
        font-weight: 850;
        letter-spacing: 0;
        max-width: 780px;
        text-wrap: balance;
        animation: login-rise 780ms cubic-bezier(.2,.8,.2,1) both;
    }
    .login-headline span {
        display: inline-block;
        background: linear-gradient(100deg, #FFFFFF 5%, #B8D6FF 34%, #FF6BCE 70%, #6EE7FF 98%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        animation: login-sheen 7s ease-in-out infinite alternate;
        background-size: 180% 100%;
    }
    .login-lede {
        margin-top: 22px;
        max-width: 650px;
        color: #AAB2C2;
        font-size: 1.08rem;
        line-height: 1.65;
        text-wrap: pretty;
        animation: login-rise 780ms cubic-bezier(.2,.8,.2,1) 120ms both;
    }
    .login-feature-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 26px;
        animation: login-rise 780ms cubic-bezier(.2,.8,.2,1) 220ms both;
    }
    .login-feature {
        border: 1px solid rgba(255,255,255,0.12);
        color: #D8DFEC;
        background: rgba(255,255,255,0.06);
        border-radius: 999px;
        padding: 9px 12px;
        font-size: 0.83rem;
        font-weight: 720;
        backdrop-filter: blur(16px);
    }
    .login-panel {
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 18px;
        padding: 24px;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.055)),
            rgba(15, 17, 25, 0.72);
        box-shadow: 0 32px 110px rgba(0,0,0,0.48);
        backdrop-filter: blur(30px) saturate(1.2);
        animation: login-panel-in 860ms cubic-bezier(.2,.8,.2,1) both;
    }
    .login-backdrop {
        position: fixed;
        inset: 0;
        pointer-events: none;
        background:
            radial-gradient(circle at 18% 16%, rgba(67, 128, 255, 0.28), transparent 28%),
            radial-gradient(circle at 82% 76%, rgba(255, 81, 196, 0.22), transparent 32%),
            radial-gradient(circle at 58% 18%, rgba(92, 229, 255, 0.12), transparent 28%);
        z-index: 0;
    }
    .login-panel-title {
        color: #FFFFFF;
        font-size: 1.35rem;
        font-weight: 820;
        margin-bottom: 5px;
    }
    .login-panel-copy {
        color: #9FA8B8;
        line-height: 1.45;
        margin-bottom: 16px;
    }
    .login-security {
        margin-top: 14px;
        border-top: 1px solid rgba(255,255,255,0.10);
        padding-top: 14px;
        color: #939BAA;
        font-size: 0.84rem;
        line-height: 1.45;
    }
    .auth-divider {
        display: flex;
        align-items: center;
        gap: 12px;
        color: #7F8796;
        font-size: 0.78rem;
        margin: 14px 0;
    }
    .auth-divider::before,
    .auth-divider::after {
        content: "";
        flex: 1;
        height: 1px;
        background: rgba(255,255,255,0.12);
    }
    div[data-testid="stLinkButton"] a {
        min-height: 48px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.22);
        background: #FFFFFF;
        color: #202124;
        font-weight: 720;
        letter-spacing: 0;
        text-transform: none;
        box-shadow: 0 1px 2px rgba(0,0,0,0.18);
        transition: transform 160ms ease, background-color 160ms ease;
    }
    div[data-testid="stLinkButton"] a:hover {
        background: #F7F8FA;
        color: #111318;
        transform: translateY(-1px);
    }
    div[data-testid="stLinkButton"] a:focus-visible {
        outline: 2px solid #6EA8FF;
        outline-offset: 2px;
    }
    div[data-testid="stTextInput"] input {
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.16);
        background: rgba(255,255,255,0.92);
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: rgba(110,168,255,0.75);
        box-shadow: 0 0 0 3px rgba(110,168,255,0.20);
    }
    @keyframes login-drift {
        from { transform: translate3d(0, 0, 0) scale(1); }
        to { transform: translate3d(34px, 24px, 0) scale(1.08); }
    }
    @keyframes login-rise {
        from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes login-panel-in {
        from { opacity: 0; transform: translateY(20px) scale(0.985); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes login-sheen {
        from { background-position: 0% 50%; }
        to { background-position: 100% 50%; }
    }
    .stApp {
        background:
            radial-gradient(circle at 50% -10%, rgba(255, 255, 255, 0.085), transparent 28%),
            linear-gradient(180deg, #090A0D 0%, #050609 62%, #050609 100%);
        color: #F7F8FA;
    }
    .block-container {
        max-width: 1380px;
        padding-top: 0.95rem;
        padding-bottom: 3rem;
    }
    div[data-testid="stTabs"] button {
        color: #A4AAB7;
        font-weight: 760;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #F5F5F7;
    }
    div[data-testid="stButton"] button {
        border-radius: 8px;
        min-height: 46px;
        font-weight: 800;
        letter-spacing: 1.8px;
        text-transform: uppercase;
        transition: background-color 160ms ease, border-color 160ms ease, transform 160ms ease;
    }
    div[data-testid="stButton"] button:hover {
        transform: translateY(-1px);
    }
    div[data-testid="stButton"] button:focus-visible,
    div[data-testid="stFileUploader"] section:focus-within {
        outline: 2px solid #6EA8FF;
        outline-offset: 2px;
    }
    div[data-testid="stFileUploader"] {
        max-width: 820px;
        margin: 10px auto 18px;
    }
    div[data-testid="stFileUploader"] label {
        display: none;
    }
    div[data-testid="stFileUploader"] section {
        min-height: 292px;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.10);
        background:
            linear-gradient(180deg, rgba(255,255,255,0.085), rgba(255,255,255,0.028)),
            rgba(16, 17, 21, 0.82);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.10),
            0 28px 90px rgba(0,0,0,0.38);
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        backdrop-filter: blur(22px);
        transition: border-color 180ms ease, background-color 180ms ease, transform 180ms ease;
    }
    div[data-testid="stFileUploader"] section:hover {
        border-color: rgba(0, 113, 227, 0.46);
        transform: translateY(-1px);
    }
    div[data-testid="stFileUploader"] section small {
        color: #8E8E93;
    }
    div[data-testid="stFileUploader"] button {
        width: 86px;
        height: 86px;
        border-radius: 22px;
        color: transparent;
        background:
            linear-gradient(180deg, #FFFFFF, #E8E8ED);
        border: 1px solid rgba(255,255,255,0.68);
        box-shadow:
            0 18px 44px rgba(0,0,0,0.35),
            0 0 0 8px rgba(255,255,255,0.045);
        position: relative;
        letter-spacing: 0;
    }
    div[data-testid="stFileUploader"] button::after {
        content: "+";
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        color: #1D1D1F;
        font-size: 2.35rem;
        font-weight: 430;
    }
    .upload-intro {
        max-width: 820px;
        margin: 22px auto 0;
        text-align: center;
    }
    .upload-eyebrow {
        color: #86868B;
        font-size: 0.78rem;
        font-weight: 720;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .upload-headline {
        color: #F5F5F7;
        font-size: clamp(2.2rem, 5.6vw, 4.55rem);
        line-height: 1.04;
        font-weight: 760;
        letter-spacing: 0;
    }
    .upload-subtitle {
        color: #A1A1A6;
        font-size: clamp(1rem, 2vw, 1.25rem);
        line-height: 1.45;
        margin: 14px auto 8px;
        max-width: 560px;
    }
    .upload-microcopy {
        color: #6E6E73;
        font-size: 0.82rem;
        margin-bottom: 14px;
    }
    div[data-testid="stAlert"] {
        border-radius: 8px;
    }
    .studio-nav {
        margin: 4px auto 14px;
        min-height: 34px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }
    .brand-mark {
        display: flex;
        align-items: center;
        gap: 14px;
        color: #FFFFFF;
        font-weight: 780;
        letter-spacing: 5px;
        font-size: 0.95rem;
        min-width: 0;
    }
    .brand-orb {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: linear-gradient(180deg, #F5F5F7, #8E8E93);
        border: 1px solid rgba(255, 255, 255, 0.34);
        flex: 0 0 auto;
    }
    .nav-meta {
        color: #A9B2C2;
        font-size: 0.78rem;
        font-weight: 720;
        text-align: right;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .panel {
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 8px;
        background: rgba(9, 10, 16, 0.88);
        padding: 22px;
        box-shadow: 0 20px 55px rgba(0, 0, 0, 0.34);
    }
    .panel-title {
        color: #F4F6FA;
        font-size: 0.88rem;
        font-weight: 800;
        letter-spacing: 6px;
        text-transform: uppercase;
        margin-bottom: 14px;
    }
    .metric-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin: 10px 0 16px;
    }
    .metric-pill {
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 8px;
        padding: 8px 10px;
        color: #C7CEDB;
        background: rgba(255,255,255,0.04);
        font-size: 0.82rem;
        font-variant-numeric: tabular-nums;
    }
    .face-list-note {
        color: #9EA6B5;
        font-size: 0.82rem;
        margin: 0 0 8px;
    }
    .face-preview img {
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.04);
        aspect-ratio: 1 / 1;
        object-fit: cover;
    }
    .face-title {
        color: #F5F5F7;
        font-size: 0.98rem;
        font-weight: 760;
        margin: 0 0 5px;
    }
    .face-meta {
        color: #AAB2C1;
        font-size: 0.78rem;
        line-height: 1.45;
        font-variant-numeric: tabular-nums;
        overflow-wrap: anywhere;
    }
    .muted {
        color: #9399A6;
        font-size: 0.86rem;
    }
    .output-line {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 9px 10px;
        margin: 6px 0;
        background: rgba(255,255,255,0.035);
        color: #C9D1DF;
        overflow-wrap: anywhere;
        font-size: 0.84rem;
    }
    .active-file-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 14px;
        padding: 14px 16px;
        margin: 0 0 18px;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.075), rgba(255,255,255,0.028)),
            rgba(14, 15, 20, 0.86);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
    }
    .active-file-name {
        color: #F5F5F7;
        font-size: 0.98rem;
        font-weight: 760;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .active-file-meta {
        color: #8E8E93;
        font-size: 0.8rem;
        margin-top: 3px;
    }
    .output-card {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 10px;
        margin: 8px 0;
        background: rgba(255,255,255,0.035);
    }
    .output-card-title {
        color: #F5F5F7;
        font-size: 0.84rem;
        font-weight: 760;
        overflow-wrap: anywhere;
    }
    .output-card-url {
        color: #8F98A8;
        font-size: 0.72rem;
        line-height: 1.35;
        margin: 4px 0 8px;
        overflow-wrap: anywhere;
    }
    @media (max-width: 900px) {
        .login-panel {
            padding: 18px;
        }
        .studio-nav {
            align-items: flex-start;
            flex-direction: column;
            padding: 16px;
        }
        .nav-meta {
            max-width: 100%;
            text-align: left;
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .login-headline,
        .login-headline span,
        .login-lede,
        .login-feature-row,
        .login-panel {
            animation: none;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=10)
def load_api_config():
    try:
        response = api_get("/config", timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "api_available": False,
            "supabase_enabled": False,
            "storage_provider": "unknown",
            "error": str(exc),
        }
    config = response.json()
    config["api_available"] = True
    return config


@st.cache_data(ttl=30)
def load_face_enhance_config(auth_token=None):
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    try:
        response = api_get("/api/v1/face-enhance/config", headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "api_available": False,
            "error": str(exc),
            "characters": [],
            "default_character_id": None,
        }
    config = response.json()
    config["api_available"] = True
    return config


def auth_headers():
    token = st.session_state.get("auth_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def absolute_url(url):
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{API_URL}{url}"


def image_content_type(filename, content_type=None):
    if content_type in {"image/jpeg", "image/png"}:
        return content_type
    extension = os.path.splitext(filename or "")[1].lower()
    if extension in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if extension == ".png":
        return "image/png"
    return "application/octet-stream"


def save_auth_session(auth_payload):
    token = auth_payload.get("access_token")
    user = auth_payload.get("user") or {}
    if token:
        st.session_state.auth_token = token
        st.session_state.auth_refresh_token = auth_payload.get("refresh_token")
        st.session_state.auth_expires_at = auth_payload.get("expires_at")
        st.session_state.auth_user = user
        st.rerun()
    else:
        st.sidebar.info(auth_payload.get("message", "Account created. Login may require email confirmation."))


def google_oauth_start_url():
    return f"{API_URL}/auth/google/start?{urlencode({'app_redirect': AIFX_FRONTEND_URL})}"


def consume_oauth_return():
    oauth_error = st.query_params.get("oauth_error")
    oauth_ticket = st.query_params.get("oauth_ticket")
    if oauth_error:
        st.query_params.clear()
        st.session_state.auth_notice = f"Google login failed: {oauth_error}"
        st.rerun()
    if not oauth_ticket:
        return

    try:
        response = api_post(
            "/auth/google/complete",
            json={"ticket": oauth_ticket},
            timeout=20,
        )
        response.raise_for_status()
        auth_payload = response.json()
    except requests.RequestException as exc:
        st.query_params.clear()
        st.session_state.auth_notice = f"Google login failed while creating the AIFX session: {exc}"
        st.rerun()

    st.query_params.clear()
    save_auth_session(auth_payload)


def submit_auth(auth_mode, email, password, location):
    endpoint = "login" if auth_mode == "Login" else "signup"
    try:
        response = api_post(
            f"/auth/{endpoint}",
            json={"email": email, "password": password},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        location.error(f"{auth_mode} failed: {exc}")
    else:
        auth_payload = response.json()
        if auth_payload.get("access_token"):
            save_auth_session(auth_payload)
        else:
            location.info(auth_payload.get("message", "Account created. Login may require email confirmation."))


def handle_request_error(exc, location, action):
    message = str(exc)
    if "401" in message or "Unauthorized" in message:
        st.session_state.pop("auth_token", None)
        st.session_state.pop("auth_refresh_token", None)
        st.session_state.pop("auth_expires_at", None)
        st.session_state.pop("auth_user", None)
        st.session_state.auth_notice = "Your login expired. Please sign in again, then continue."
        st.rerun()
    location.error(f"{action} failed: {exc}")


def render_login_page():
    st.markdown(
        """
        <div class="login-backdrop"></div>
        """,
        unsafe_allow_html=True,
    )
    intro_col, form_col = st.columns([0.62, 0.38], gap="large")
    with intro_col:
        st.markdown(
            """
            <section class="login-copy">
                <div class="login-kicker"><span class="login-dot"></span> Private AI face workspace</div>
                <div class="login-headline">AIFX <span>Studio</span></div>
                <div class="login-lede">
                    Sign in to detect every candidate face, review crop regions, and keep each output tied to your private task history.
                </div>
                <div class="login-feature-row">
                    <div class="login-feature">Recall-first detection</div>
                    <div class="login-feature">Selectable crops</div>
                    <div class="login-feature">Supabase history</div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
    with form_col:
        st.markdown(
            """
            <div class="login-panel">
                <div class="login-panel-title">Welcome back</div>
                <div class="login-panel-copy">Continue with Google or use your AIFX email account.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.link_button(
            "Continue with Google",
            google_oauth_start_url(),
            icon=":material/account_circle:",
            use_container_width=True,
        )
        st.markdown('<div class="auth-divider">or use email</div>', unsafe_allow_html=True)
        auth_mode = st.radio("Account action", ["Login", "Sign up"], horizontal=True, label_visibility="collapsed")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Password")
        if st.session_state.get("auth_notice"):
            st.info(st.session_state.pop("auth_notice"))
        if st.button(auth_mode, type="primary", use_container_width=True):
            submit_auth(auth_mode, email, password, st)
        st.markdown(
            """
            <div class="login-security">
                Use an app account, not your Supabase admin login. Your browser keeps the session while the app is running.
            </div>
            """,
            unsafe_allow_html=True,
        )


api_config = load_api_config()
supabase_enabled = api_config.get("supabase_enabled", False)

if not api_config.get("api_available"):
    st.error(f"Backend unavailable: {api_config.get('error')}")
    st.stop()

if supabase_enabled and not st.session_state.get("auth_token"):
    consume_oauth_return()
    render_login_page()
    st.stop()

current_user = st.session_state.get("auth_user") or {}
nav_user = escape(current_user.get("email") or "Local workspace")
provider_label = escape(str(api_config.get("storage_provider", "unknown")).upper())
st.markdown(
    f"""
    <div class="studio-nav">
        <div class="brand-mark"><div class="brand-orb"></div><div>AIFX</div></div>
        <div class="nav-meta">{provider_label} · {nav_user}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.header("Session")
if supabase_enabled:
    user = st.session_state.get("auth_user") or {}
    st.sidebar.markdown(
        f"""
        <div class="account-panel">
            <div class="account-kicker">Cloud account</div>
            <div class="account-title">{user.get('email') or 'Signed in user'}</div>
            <div class="account-copy">Uploads are saved to Supabase Storage and task history is private to this account.</div>
            <span class="mode-pill">SUPABASE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Sign out", use_container_width=True):
        st.session_state.pop("auth_token", None)
        st.session_state.pop("auth_refresh_token", None)
        st.session_state.pop("auth_expires_at", None)
        st.session_state.pop("auth_user", None)
        st.rerun()
else:
    st.sidebar.markdown(
        """
        <div class="account-panel">
            <div class="account-kicker">Local demo</div>
            <div class="account-title">No cloud connection</div>
            <div class="account-copy">Uploads and task history stay in the project storage folder.</div>
            <span class="mode-pill local">LOCAL</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.sidebar.caption(f"Storage provider: {api_config.get('storage_provider', 'unknown')}")
st.sidebar.header("Detection Controls")
st.sidebar.caption("Lower values find more small/side faces, but may add false positives.")


def clamp_value(value, minimum, maximum):
    return min(maximum, max(minimum, round(float(value), 2)))


def init_control_defaults():
    if st.session_state.get("control_defaults_version") == CONTROL_DEFAULTS_VERSION:
        return
    st.session_state.full_range_confidence = DEFAULT_FULL_RANGE_CONFIDENCE
    st.session_state.full_range_confidence_slider = DEFAULT_FULL_RANGE_CONFIDENCE
    st.session_state.full_range_confidence_input = DEFAULT_FULL_RANGE_CONFIDENCE
    st.session_state.short_range_confidence = DEFAULT_SHORT_RANGE_CONFIDENCE
    st.session_state.short_range_confidence_slider = DEFAULT_SHORT_RANGE_CONFIDENCE
    st.session_state.short_range_confidence_input = DEFAULT_SHORT_RANGE_CONFIDENCE
    st.session_state.min_suppression_threshold = DEFAULT_SUPPRESSION_THRESHOLD
    st.session_state.min_suppression_threshold_slider = DEFAULT_SUPPRESSION_THRESHOLD
    st.session_state.min_suppression_threshold_input = DEFAULT_SUPPRESSION_THRESHOLD
    st.session_state.control_defaults_version = CONTROL_DEFAULTS_VERSION


def init_control_state(name, default, minimum, maximum):
    value = clamp_value(st.session_state.get(name, default), minimum, maximum)
    st.session_state[name] = value


init_control_defaults()
init_control_state("full_range_confidence", DEFAULT_FULL_RANGE_CONFIDENCE, 0.01, 0.99)
init_control_state("short_range_confidence", DEFAULT_SHORT_RANGE_CONFIDENCE, 0.01, 0.99)
init_control_state("min_suppression_threshold", DEFAULT_SUPPRESSION_THRESHOLD, 0.01, 0.99)
init_control_state("crop_scale", 2.2, 1.0, 5.0)
init_control_state("shoulder_bias", 0.2, -1.5, 1.5)


def sync_full_range_confidence_slider():
    value = clamp_value(st.session_state.full_range_confidence_slider, 0.01, 0.99)
    st.session_state.full_range_confidence = value
    st.session_state.full_range_confidence_input = value


def sync_full_range_confidence_input():
    value = clamp_value(st.session_state.full_range_confidence_input, 0.01, 0.99)
    st.session_state.full_range_confidence = value
    st.session_state.full_range_confidence_slider = value


def sync_short_range_confidence_slider():
    value = clamp_value(st.session_state.short_range_confidence_slider, 0.01, 0.99)
    st.session_state.short_range_confidence = value
    st.session_state.short_range_confidence_input = value


def sync_short_range_confidence_input():
    value = clamp_value(st.session_state.short_range_confidence_input, 0.01, 0.99)
    st.session_state.short_range_confidence = value
    st.session_state.short_range_confidence_slider = value


def sync_min_suppression_threshold_slider():
    value = clamp_value(st.session_state.min_suppression_threshold_slider, 0.01, 0.99)
    st.session_state.min_suppression_threshold = value
    st.session_state.min_suppression_threshold_input = value


def sync_min_suppression_threshold_input():
    value = clamp_value(st.session_state.min_suppression_threshold_input, 0.01, 0.99)
    st.session_state.min_suppression_threshold = value
    st.session_state.min_suppression_threshold_slider = value


def sync_crop_scale_slider():
    value = clamp_value(st.session_state.crop_scale_slider, 1.0, 5.0)
    st.session_state.crop_scale = value
    st.session_state.crop_scale_input = value


def sync_crop_scale_input():
    value = clamp_value(st.session_state.crop_scale_input, 1.0, 5.0)
    st.session_state.crop_scale = value
    st.session_state.crop_scale_slider = value


def sync_shoulder_bias_slider():
    value = clamp_value(st.session_state.shoulder_bias_slider, -1.5, 1.5)
    st.session_state.shoulder_bias = value
    st.session_state.shoulder_bias_input = value


def sync_shoulder_bias_input():
    value = clamp_value(st.session_state.shoulder_bias_input, -1.5, 1.5)
    st.session_state.shoulder_bias = value
    st.session_state.shoulder_bias_slider = value


def linked_slider_number(
    label,
    state_name,
    minimum,
    maximum,
    slider_callback,
    input_callback,
    suffix="",
    help_text=None,
    container=None,
):
    parent = container or st.sidebar
    slider_col, input_col = parent.columns([0.68, 0.32])
    slider_value = {}
    input_value = {}
    if f"{state_name}_slider" not in st.session_state:
        slider_value["value"] = st.session_state[state_name]
    if f"{state_name}_input" not in st.session_state:
        input_value["value"] = st.session_state[state_name]
    with slider_col:
        st.slider(
            label,
            min_value=minimum,
            max_value=maximum,
            step=0.01,
            key=f"{state_name}_slider",
            on_change=slider_callback,
            help=help_text,
            **slider_value,
        )
    with input_col:
        st.number_input(
            "Exact value",
            min_value=minimum,
            max_value=maximum,
            step=0.01,
            format="%.2f",
            key=f"{state_name}_input",
            on_change=input_callback,
            label_visibility="collapsed",
            help=help_text,
            **input_value,
        )
    parent.caption(f"{label}: {st.session_state[state_name]:.2f}{suffix}")


st.sidebar.markdown(
    f"""
    <div class="account-panel">
        <div class="account-kicker">Detection strategy</div>
        <div class="account-title">{BEST_DETECTION_LABEL}</div>
        <div class="account-copy">Runs short-range then full-range MediaPipe detection, then merges duplicates by confidence.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
linked_slider_number(
    "Distant-face sensitivity",
    "full_range_confidence",
    0.01,
    0.99,
    sync_full_range_confidence_slider,
    sync_full_range_confidence_input,
    help_text=(
        "Lower this when small or far-away faces are missing. "
        "Lower values may add more false positives."
    ),
)
linked_slider_number(
    "Close-face sensitivity",
    "short_range_confidence",
    0.01,
    0.99,
    sync_short_range_confidence_slider,
    sync_short_range_confidence_input,
    help_text=(
        "Lower this when large close faces are missing. "
        "Raise it if the result has too many obvious false positives."
    ),
)
linked_slider_number(
    "Min Suppression Threshold",
    "min_suppression_threshold",
    0.01,
    0.99,
    sync_min_suppression_threshold_slider,
    sync_min_suppression_threshold_input,
    help_text=(
        "Controls how strongly overlapping detections are merged. "
        "Lower values remove more duplicate boxes; higher values keep more nearby boxes."
    ),
)

with st.sidebar.expander("Crop box tuning", expanded=False):
    linked_slider_number(
        "Crop expansion",
        "crop_scale",
        1.0,
        5.0,
        sync_crop_scale_slider,
        sync_crop_scale_input,
        "x",
        help_text=(
            "Controls how much the detected face is expanded into the final square crop. "
            "Larger values include more hair, neck, shoulders, and background."
        ),
        container=st,
    )
    linked_slider_number(
        "Vertical offset",
        "shoulder_bias",
        -1.5,
        1.5,
        sync_shoulder_bias_slider,
        sync_shoulder_bias_input,
        help_text=(
            "Controls vertical crop position. Negative values move the square crop upward, "
            "0 keeps it centered, and positive values move it downward to include more shoulders."
        ),
        container=st,
    )


def draw_detection_overlay(image_bytes, faces):
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    line_width = max(3, int(max(image.size) / 260))

    for face in faces:
        bbox = face["crop_bbox"]
        face_bbox = face["face_bbox"]
        x_min = int(bbox["x_min"])
        y_min = int(bbox["y_min"])
        x_max = x_min + int(bbox["width"])
        y_max = y_min + int(bbox["height"])
        label = (
            f"Face {face['face_index']} | "
            f"crop x={x_min} y={y_min} w={int(bbox['width'])} h={int(bbox['height'])} | "
            f"face {face_bbox['confidence']:.2f} {face_bbox.get('model_range', '')}"
        )

        draw.rectangle((x_min, y_min, x_max, y_max), outline="#00E676", width=line_width)
        label_bbox = draw.textbbox((x_min, y_min), label)
        label_height = label_bbox[3] - label_bbox[1]
        label_width = label_bbox[2] - label_bbox[0]
        label_y = max(0, y_min - label_height - line_width * 2)
        draw.rectangle(
            (x_min, label_y, x_min + label_width + line_width * 2, label_y + label_height + line_width * 2),
            fill="#00E676",
        )
        draw.text((x_min + line_width, label_y + line_width), label, fill="#111111")

    return image

def reset_detection_state():
    st.session_state.pop("detection_result", None)
    st.session_state.pop("uploaded_image_bytes", None)
    st.session_state.pop("uploaded_filename", None)
    st.session_state.pop("uploaded_content_type", None)
    st.session_state.pop("crop_result", None)
    st.session_state.pop("select_all_faces", None)
    st.session_state.pop("phase2_job_id", None)
    st.session_state.pop("phase2_job", None)
    st.session_state.upload_uploader_version = st.session_state.get("upload_uploader_version", 0) + 1
    for key in list(st.session_state.keys()):
        if str(key).startswith("select_face_"):
            st.session_state.pop(key, None)


def selected_face_indices(faces):
    return [
        face["face_index"]
        for face in faces
        if st.session_state.get(f"select_face_{face['face_index']}", False)
    ]


def normalize_character_catalog(face_enhance_config):
    characters = face_enhance_config.get("characters", [])
    catalog = {}
    if isinstance(characters, dict):
        iterable = characters.items()
        for character_id, details in iterable:
            catalog[character_id] = {
                "character_id": character_id,
                "display_name": details.get("display_name", character_id),
            }
    else:
        for character in characters:
            if isinstance(character, str):
                catalog[character] = {
                    "character_id": character,
                    "display_name": character.replace("_", " ").title(),
                }
            else:
                character_id = character.get("character_id")
                if character_id:
                    catalog[character_id] = {
                        "character_id": character_id,
                        "display_name": character.get("display_name", character_id),
                    }
    return catalog


def build_enhancement_plan(crop_result, character_catalog):
    faces = []
    for face in crop_result.get("faces", []):
        key = f"target_character_{crop_result['task_id']}_{face['output_index']}"
        character_id = st.session_state.get(key)
        character = character_catalog.get(character_id, {})
        faces.append(
            {
                "output_index": face["output_index"],
                "face_index": face["face_index"],
                "crop_url": face["url"],
                "crop_filename": face["filename"],
                "crop_bbox": face["crop_bbox"],
                "face_bbox": face["face_bbox"],
                "target_character_id": character_id,
                "target_display_name": character.get("display_name", character_id),
                "planned_steps": [
                    "enhance_crop_with_selected_lora",
                    "resize_enhanced_crop_to_crop_bbox",
                    "feather_blend_enhanced_crop_into_original_image",
                ],
            }
        )

    return {
        "task_id": crop_result["task_id"],
        "source_filename": crop_result.get("filename"),
        "original_image_url": crop_result.get("original_image_url"),
        "image_width": crop_result.get("image_width"),
        "image_height": crop_result.get("image_height"),
        "queue_endpoint": "/api/v1/enhancement-jobs",
        "blend_strategy": {
            "target_region": "crop_bbox",
            "mask": "gaussian_feather_mask",
            "feather_radius_px": 24,
            "placement": "paste enhanced crop back into original image coordinates",
        },
        "faces": faces,
    }


def queue_enhancement_job(
    *,
    image_bytes,
    uploaded_name,
    uploaded_type,
    enhancement_plan,
    feather_radius=24,
    max_retries=3,
):
    files = [
        (
            "original",
            (
                uploaded_name or "original.png",
                image_bytes,
                uploaded_type,
            ),
        )
    ]
    face_specs = []
    for output_index, face in enumerate(enhancement_plan["faces"], start=1):
        crop_bytes = base64.b64decode(
            st.session_state.crop_result["faces"][output_index - 1]["preview_base64"]
        )
        files.append(
            (
                "crops",
                (face["crop_filename"], crop_bytes, "image/png"),
            )
        )
        face_specs.append(
            {
                "face_id": f"face_{face['face_index']:03d}",
                "crop_bbox": face["crop_bbox"],
                "face_bbox": face["face_bbox"],
                "character_id": face["target_character_id"],
                "prompt": "",
            }
        )
    return api_post(
        "/api/v1/enhancement-jobs",
        files=files,
        data={
            "faces_json": json.dumps(face_specs),
            "feather_radius": str(feather_radius),
            "max_retries": str(max_retries),
        },
        headers=auth_headers(),
        timeout=120,
    )


def load_enhancement_job(job_id):
    response = api_get(
        f"/api/v1/enhancement-jobs/{job_id}",
        headers=auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def remote_image_bytes(url):
    response = LOCAL_API_SESSION.get(absolute_url(url), timeout=60)
    response.raise_for_status()
    return response.content


tab_workspace, tab_history, tab_enhancements = st.tabs(["Workspace", "Crop History", "Enhancements"])

with tab_workspace:
    image_bytes = st.session_state.get("uploaded_image_bytes")
    uploaded_name = st.session_state.get("uploaded_filename")
    uploaded_type = st.session_state.get("uploaded_content_type", "application/octet-stream")

    if image_bytes is None:
        st.markdown(
            """
            <div class="upload-intro">
                <div class="upload-eyebrow">AIFX FACE CROP</div>
                <div class="upload-headline">Start with one photo.</div>
                <div class="upload-subtitle">Add a group image, review detected faces, then save only the crops you choose.</div>
                <div class="upload-microcopy">JPG or PNG - crops are created after selection</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "Upload group photo",
            type=["jpg", "jpeg", "png"],
            help="Click the plus button or drop a JPG/PNG here.",
            label_visibility="collapsed",
            key=f"workspace_uploader_{st.session_state.get('upload_uploader_version', 0)}",
        )
        if uploaded_file is not None:
            reset_detection_state()
            st.session_state.uploaded_image_bytes = uploaded_file.getvalue()
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.uploaded_content_type = image_content_type(uploaded_file.name, uploaded_file.type)
            st.rerun()
        st.caption("Click the add button or drop a photo into the upload area.")

    if image_bytes is not None:
        st.markdown(
            f"""
            <div class="active-file-card">
                <div>
                    <div class="active-file-name">{escape(uploaded_name or "Uploaded image")}</div>
                    <div class="active-file-meta">One active image - replace it to start a new workspace</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Change Image", use_container_width=True):
            reset_detection_state()
            st.rerun()

        left_panel, right_panel = st.columns([0.62, 0.38], gap="large")
        with left_panel:
            st.markdown('<div class="panel-title">Image Workspace</div>', unsafe_allow_html=True)
            detection_result = st.session_state.get("detection_result")
            if detection_result and detection_result.get("faces"):
                overlay = draw_detection_overlay(image_bytes, detection_result["faces"])
                st.image(overlay, caption="Detected crop regions on the original image", width="stretch")
            else:
                st.image(image_bytes, caption="Original image", width="stretch")

            detect_label = "Run Detection Again" if detection_result else "Detect All Faces"
            if st.button(detect_label, type="primary", use_container_width=True):
                status_slot = st.empty()
                with status_slot:
                    st.info("Running MediaPipe detection...")
                with st.spinner("Detecting candidate faces…"):
                    files = {
                        "file": (
                            uploaded_name or "upload.png",
                            image_bytes,
                            uploaded_type,
                        )
                    }
                    data = {
                        "min_detection_confidence": min(
                            st.session_state.full_range_confidence,
                            st.session_state.short_range_confidence,
                        ),
                        "detection_range": BEST_DETECTION_RANGE,
                        "full_range_confidence": st.session_state.full_range_confidence,
                        "short_range_confidence": st.session_state.short_range_confidence,
                        "min_suppression_threshold": st.session_state.min_suppression_threshold,
                        "delegate": "gpu",
                        "crop_scale": st.session_state.crop_scale,
                        "shoulder_bias": st.session_state.shoulder_bias,
                    }
                    try:
                        response = api_post(
                            "/detect-faces",
                            files=files,
                            data=data,
                            headers=auth_headers(),
                            timeout=60,
                        )
                        response.raise_for_status()
                    except requests.RequestException as exc:
                        handle_request_error(exc, st, "Detection request")
                    else:
                        st.session_state.detection_result = response.json()
                        st.session_state.pop("crop_result", None)
                        st.session_state.pop("select_all_faces", None)
                        for key in list(st.session_state.keys()):
                            if str(key).startswith("select_face_"):
                                st.session_state.pop(key, None)
                        st.rerun()
                status_slot.empty()

            detection_result = st.session_state.get("detection_result")
            if detection_result:
                metric_items = [
                    f"Task {detection_result['task_id'][:8]}",
                    f"{detection_result['face_count']} detected",
                    BEST_DETECTION_LABEL,
                ]
                if (
                    detection_result.get("full_range_confidence") is not None
                    and detection_result.get("short_range_confidence") is not None
                ):
                    metric_items.append(
                        f"full {detection_result['full_range_confidence']:.2f} · "
                        f"short {detection_result['short_range_confidence']:.2f}"
                    )
                metric_items.extend(
                    [
                        "short then full",
                        "4-tile distant scan",
                        "confidence sorted",
                        f"{detection_result['image_width']} x {detection_result['image_height']}",
                        detection_result["storage_provider"],
                    ]
                )
                metric_html = "".join(f'<div class="metric-pill">{escape(str(item))}</div>' for item in metric_items)
                st.markdown(f'<div class="metric-row">{metric_html}</div>', unsafe_allow_html=True)

        with right_panel:
            st.markdown('<div class="panel-title">Detected Faces</div>', unsafe_allow_html=True)
            detection_result = st.session_state.get("detection_result")
            if not detection_result:
                st.info("Run detection to review face candidates. No crop files are saved at this stage.")
            elif not detection_result.get("faces"):
                st.warning("No faces detected. Try lowering the confidence threshold or increasing crop expansion.")
            else:
                faces = detection_result["faces"]
                select_all = st.checkbox("Select all detected faces", key="select_all_faces")
                if select_all:
                    for face in faces:
                        st.session_state[f"select_face_{face['face_index']}"] = True

                st.markdown(
                    f'<div class="face-list-note">{len(faces)} candidates sorted by confidence. Scroll this list only.</div>',
                    unsafe_allow_html=True,
                )
                face_list = st.container(height=430, border=True)
                with face_list:
                    for face in faces:
                        face_bbox = face["face_bbox"]
                        crop_bbox = face["crop_bbox"]
                        with st.container(border=True):
                            preview_col, detail_col = st.columns([0.36, 0.64], gap="small")
                            with preview_col:
                                preview_bytes = base64.b64decode(face["preview_base64"])
                                st.image(
                                    BytesIO(preview_bytes),
                                    width="stretch",
                                )
                            with detail_col:
                                st.markdown(
                                    f'<div class="face-title">Crop {face["face_index"]}</div>',
                                    unsafe_allow_html=True,
                                )
                                st.checkbox(
                                    "Select this crop",
                                    key=f"select_face_{face['face_index']}",
                                )
                                with st.expander("Coordinates", expanded=False):
                                    st.markdown(
                                        f"""
                                        <div class="face-meta">
                                            crop x={crop_bbox['x_min']} y={crop_bbox['y_min']} w={crop_bbox['width']} h={crop_bbox['height']}<br>
                                            face x={face_bbox['x_min']} y={face_bbox['y_min']} w={face_bbox['width']} h={face_bbox['height']} · confidence {face_bbox['confidence']:.2f} · {escape(face_bbox.get('model_range', 'unknown'))}
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                selected_indices = selected_face_indices(faces)
                selected_count = len(selected_indices)
                st.caption(f"{selected_count} selected for output.")
                if selected_count == 0:
                    crop_button_label = "Select Faces To Save"
                elif selected_count == 1:
                    crop_button_label = "Save 1 Selected Crop"
                else:
                    crop_button_label = f"Save {selected_count} Selected Crops"
                if st.button(crop_button_label, type="primary", use_container_width=True, disabled=not selected_indices):
                    with st.spinner("Cropping and saving selected faces…"):
                        try:
                            response = api_post(
                                "/crop-selected",
                                json={
                                    "task_id": detection_result["task_id"],
                                    "selected_face_indices": selected_indices,
                                },
                                headers=auth_headers(),
                                timeout=60,
                            )
                            response.raise_for_status()
                        except requests.RequestException as exc:
                            handle_request_error(exc, st, "Crop request")
                        else:
                            crop_result = response.json()
                            st.session_state.crop_result = crop_result
                            st.success(crop_result["message"])
                if st.session_state.get("crop_result"):
                    st.markdown('<div class="panel-title">Saved Output</div>', unsafe_allow_html=True)
                    crop_result = st.session_state.crop_result
                    face_enhance_config = load_face_enhance_config(st.session_state.get("auth_token"))
                    character_catalog = normalize_character_catalog(face_enhance_config)
                    default_character_id = face_enhance_config.get("default_character_id")
                    character_options = list(character_catalog)
                    output_list = st.container(height=430, border=True)
                    with output_list:
                        for face in crop_result.get("faces", []):
                            crop_bytes = base64.b64decode(face["preview_base64"])
                            preview_col, download_col = st.columns([0.34, 0.66], gap="small")
                            with preview_col:
                                st.image(BytesIO(crop_bytes), width="stretch")
                            with download_col:
                                st.markdown(
                                    f"""
                                    <div class="output-card">
                                        <div class="output-card-title">{escape(face['filename'])}</div>
                                        <div class="output-card-url">{escape(absolute_url(face['url']))}</div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                                st.download_button(
                                    "Download crop",
                                    data=crop_bytes,
                                    file_name=face["filename"],
                                    mime="image/png",
                                    key=f"download_crop_{face['output_index']}_{face['filename']}",
                                    use_container_width=True,
                                )
                                target_key = f"target_character_{crop_result['task_id']}_{face['output_index']}"
                                if character_options:
                                    if target_key not in st.session_state:
                                        st.session_state[target_key] = (
                                            default_character_id
                                            if default_character_id in character_catalog
                                            else character_options[0]
                                        )
                                    st.selectbox(
                                        "Target character",
                                        character_options,
                                        key=target_key,
                                        format_func=lambda character_id: (
                                            character_catalog.get(character_id, {}).get("display_name", character_id)
                                        ),
                                        help="Choose the private character preset used to enhance or replace this crop.",
                                    )
                                else:
                                    st.warning(
                                        f"LoRA catalog unavailable: {face_enhance_config.get('error', 'unknown error')}"
                                    )
                            st.divider()
                    if character_options:
                        enhancement_plan = build_enhancement_plan(crop_result, character_catalog)
                        plan_json = json.dumps(enhancement_plan, indent=2)
                        st.markdown('<div class="panel-title">Enhancement Plan</div>', unsafe_allow_html=True)
                        st.caption(
                            "This plan records the character selection and coordinates for each crop."
                        )
                        st.download_button(
                            "Download enhancement plan JSON",
                            data=plan_json,
                            file_name=f"{crop_result['task_id']}-enhancement-plan.json",
                            mime="application/json",
                            use_container_width=True,
                        )
                        with st.expander("Preview enhancement plan", expanded=False):
                            st.json(enhancement_plan)

                        phase2_job_id = st.session_state.get("phase2_job_id")
                        if not phase2_job_id:
                            queue_disabled = not api_config.get("supabase_enabled")
                            if st.button(
                                "Upload To Cloud And Queue Enhancement",
                                type="primary",
                                use_container_width=True,
                                disabled=queue_disabled,
                            ):
                                with st.spinner("Uploading original and selected crops to cloud storage…"):
                                    try:
                                        response = queue_enhancement_job(
                                            image_bytes=image_bytes,
                                            uploaded_name=uploaded_name,
                                            uploaded_type=uploaded_type,
                                            enhancement_plan=enhancement_plan,
                                        )
                                        response.raise_for_status()
                                    except requests.RequestException as exc:
                                        handle_request_error(exc, st, "Could not create enhancement job")
                                    else:
                                        job = response.json()
                                        st.session_state.phase2_job_id = job["job_id"]
                                        st.session_state.phase2_job = job
                                        st.rerun()
                            if queue_disabled:
                                st.caption("Cloud queue requires Supabase to be enabled in the backend.")

                        phase2_job_id = st.session_state.get("phase2_job_id")
                        if phase2_job_id:
                            refresh_col, clear_col = st.columns(2)
                            with refresh_col:
                                if st.button("Refresh Job Status", use_container_width=True):
                                    try:
                                        st.session_state.phase2_job = load_enhancement_job(phase2_job_id)
                                    except requests.RequestException as exc:
                                        handle_request_error(exc, st, "Could not refresh enhancement job")
                                    else:
                                        st.rerun()
                            with clear_col:
                                if st.button("Hide Job", use_container_width=True):
                                    st.session_state.pop("phase2_job_id", None)
                                    st.session_state.pop("phase2_job", None)
                                    st.rerun()

                            job = st.session_state.get("phase2_job") or {}
                            job_faces = job.get("faces", [])
                            completed_count = sum(face.get("status") == "completed" for face in job_faces)
                            st.markdown(
                                f"**Job {escape(phase2_job_id)}** · {escape(job.get('status', 'queued'))} · "
                                f"{completed_count}/{len(job_faces)} faces complete"
                            )
                            if job.get("last_error"):
                                st.error(job["last_error"])

                            comparison = st.container(height=430, border=True)
                            with comparison:
                                if job.get("original_url"):
                                    st.caption("Original")
                                    st.image(job["original_url"], width="stretch")
                                for face in job_faces:
                                    st.caption(
                                        f"{face.get('face_id', 'face')} · "
                                        f"{face.get('status', 'queued')} · "
                                        f"{character_catalog.get(face.get('character_id'), {}).get('display_name', face.get('character_id'))}"
                                    )
                                    if face.get("enhanced_crop_url"):
                                        st.image(face["enhanced_crop_url"], width="stretch")
                                    if face.get("status") == "failed":
                                        if st.button(
                                            "Retry This Face",
                                            key=f"retry_face_{face['id']}",
                                            use_container_width=True,
                                        ):
                                            try:
                                                response = api_post(
                                                    f"/api/v1/enhancement-jobs/{phase2_job_id}/retry-face",
                                                    json={"face_id": face["id"]},
                                                    headers=auth_headers(),
                                                    timeout=30,
                                                )
                                                response.raise_for_status()
                                                st.session_state.phase2_job = load_enhancement_job(phase2_job_id)
                                            except requests.RequestException as exc:
                                                handle_request_error(exc, st, "Could not retry face")
                                            else:
                                                st.rerun()
                                if job.get("enhanced_original_url"):
                                    st.caption("Final blended image")
                                    st.image(job["enhanced_original_url"], width="stretch")
                            if job.get("enhanced_original_url"):
                                try:
                                    final_bytes = remote_image_bytes(job["enhanced_original_url"])
                                except requests.RequestException:
                                    st.caption("Final image is available in cloud storage, but download is temporarily unavailable.")
                                else:
                                    st.download_button(
                                        "Download Final Image",
                                        data=final_bytes,
                                        file_name=f"{phase2_job_id}-enhanced-original.png",
                                        mime="image/png",
                                        use_container_width=True,
                                    )

with tab_history:
    try:
        response = api_get("/tasks?limit=10", headers=auth_headers(), timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        handle_request_error(exc, st, "Could not load task history")
    else:
        history = response.json()
        tasks = history.get("tasks", [])
        st.caption(
            f"Storage provider: {history.get('storage_provider')} | "
            f"User: {history.get('user_id')}"
        )
        st.caption("Showing the latest 10 tasks. New detections appear here after the next refresh.")
        if not tasks:
            st.info("No task history yet.")
        for task in tasks:
            title = (
                f"{task.get('created_at', 'unknown time')} | "
                f"{task.get('filename', 'image')} | "
                f"{task.get('face_count', 0)} face(s)"
            )
            with st.expander(title):
                st.json(
                    {
                        "task_id": task.get("task_id"),
                        "status": task.get("status"),
                        "original_image_url": task.get("original_image_url"),
                        "cropped_image_urls": task.get("cropped_image_urls", []),
                        "settings": task.get("settings", {}),
                        "bounding_boxes": task.get("bounding_boxes", []),
                    }
                )


with tab_enhancements:
    try:
        response = api_get(
            "/api/v1/enhancement-jobs?limit=10",
            headers=auth_headers(),
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        handle_request_error(exc, st, "Could not load enhancement history")
    else:
        jobs = response.json().get("jobs", [])
        st.caption("Latest 10 cloud enhancement jobs.")
        if not jobs:
            st.info("No enhancement jobs yet.")
        for job in jobs:
            faces = job.get("faces", [])
            completed_count = sum(face.get("status") == "completed" for face in faces)
            title = (
                f"{job.get('job_id')} | {job.get('status')} | "
                f"{completed_count}/{len(faces)} faces"
            )
            with st.expander(title):
                preview_columns = st.columns(3)
                if job.get("original_url"):
                    with preview_columns[0]:
                        st.caption("Original")
                        st.image(job["original_url"], width="stretch")
                enhanced_urls = [
                    face.get("enhanced_crop_url")
                    for face in faces
                    if face.get("enhanced_crop_url")
                ]
                if enhanced_urls:
                    with preview_columns[1]:
                        st.caption("Enhanced crop")
                        st.image(enhanced_urls[0], width="stretch")
                if job.get("enhanced_original_url"):
                    with preview_columns[2]:
                        st.caption("Final")
                        st.image(job["enhanced_original_url"], width="stretch")
                st.json(
                    {
                        "job_id": job.get("job_id"),
                        "status": job.get("status"),
                        "created_at": job.get("created_at"),
                        "completed_at": job.get("completed_at"),
                        "face_statuses": [
                            {
                                "face_id": face.get("face_id"),
                                "status": face.get("status"),
                                "character_id": face.get("character_id"),
                                "retry_count": face.get("retry_count"),
                                "last_error": face.get("last_error"),
                            }
                            for face in faces
                        ],
                    }
                )

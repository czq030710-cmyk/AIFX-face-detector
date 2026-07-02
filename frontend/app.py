import os
import base64
from html import escape
from io import BytesIO

from PIL import Image, ImageDraw
import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


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
    .login-shell {
        min-height: 72vh;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .login-card {
        width: min(420px, 92vw);
        border: 1px solid #2A2D35;
        border-radius: 8px;
        padding: 28px 28px 20px;
        background: #151820;
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.28);
    }
    .login-brand {
        color: #F7F8FA;
        font-size: 1.75rem;
        font-weight: 760;
        margin-bottom: 6px;
    }
    .login-subtitle {
        color: #A9AFBA;
        line-height: 1.45;
        margin-bottom: 18px;
    }
    .login-note {
        color: #8D94A1;
        font-size: 0.86rem;
        line-height: 1.45;
        margin-top: 14px;
    }
    .stApp {
        background:
            radial-gradient(circle at 52% 4%, rgba(98, 58, 220, 0.22), transparent 32%),
            radial-gradient(circle at 10% 86%, rgba(15, 142, 199, 0.16), transparent 34%),
            linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0)),
            #07080D;
        color: #F7F8FA;
    }
    .block-container {
        max-width: 1420px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }
    div[data-testid="stTabs"] button {
        color: #A4AAB7;
        font-weight: 760;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #FF4B62;
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
    div[data-testid="stFileUploader"] section {
        border-radius: 8px;
        border: 1px dashed rgba(255,255,255,0.18);
        background: rgba(255,255,255,0.05);
    }
    div[data-testid="stAlert"] {
        border-radius: 8px;
    }
    .studio-nav {
        margin: 10px auto 22px;
        min-height: 66px;
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 8px;
        background: rgba(8, 9, 14, 0.90);
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.45);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 22px;
        gap: 18px;
    }
    .brand-mark {
        display: flex;
        align-items: center;
        gap: 14px;
        color: #FFFFFF;
        font-weight: 780;
        letter-spacing: 5px;
        font-size: 1.05rem;
        min-width: 0;
    }
    .brand-orb {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3D7BFF, #E84CCB);
        border: 2px solid rgba(255, 255, 255, 0.72);
        flex: 0 0 auto;
    }
    .nav-status {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        color: #A9B2C2;
        font-size: 0.82rem;
        font-weight: 780;
        text-transform: uppercase;
        min-width: 0;
        flex-wrap: wrap;
    }
    .nav-chip {
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 8px;
        padding: 7px 10px;
        background: rgba(255,255,255,0.045);
        white-space: nowrap;
    }
    .nav-chip.hot {
        color: #FFFFFF;
        border-color: rgba(95, 140, 255, 0.42);
        background: rgba(62, 111, 255, 0.18);
    }
    .nav-user {
        color: #DDE3EF;
        font-weight: 700;
        max-width: 260px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-align: right;
    }
    .studio-kicker {
        color: #8A7DFF;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 6px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .studio-title {
        color: #FFFFFF;
        font-size: clamp(2rem, 5vw, 4.1rem);
        line-height: 1.05;
        font-weight: 820;
        letter-spacing: 0;
        margin-bottom: 6px;
        text-wrap: balance;
    }
    .studio-title span {
        background: linear-gradient(90deg, #FF4DB8, #4EA2FF, #18D8FF);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }
    .studio-subtitle {
        color: #9EA4B1;
        font-size: 1rem;
        margin-bottom: 16px;
        max-width: 760px;
        text-wrap: pretty;
    }
    .flow-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin: 16px 0 18px;
    }
    .flow-step {
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 8px;
        padding: 12px;
        background: rgba(255,255,255,0.035);
        min-width: 0;
    }
    .flow-step.active {
        border-color: rgba(255, 75, 98, 0.58);
        background: linear-gradient(135deg, rgba(255,75,98,0.18), rgba(62,111,255,0.08));
    }
    .flow-num {
        color: #FF4B62;
        font-size: 0.72rem;
        font-weight: 840;
        letter-spacing: 2px;
        margin-bottom: 5px;
    }
    .flow-label {
        color: #FFFFFF;
        font-weight: 780;
        font-size: 0.95rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .flow-copy {
        color: #9299A8;
        font-size: 0.82rem;
        line-height: 1.35;
        margin-top: 4px;
    }
    .panel,
    .empty-panel {
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 8px;
        background: rgba(9, 10, 16, 0.88);
        padding: 22px;
        box-shadow: 0 20px 55px rgba(0, 0, 0, 0.34);
    }
    .empty-panel {
        min-height: 340px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        border-style: dashed;
    }
    .empty-icon {
        width: 54px;
        height: 54px;
        border-radius: 8px;
        display: grid;
        place-items: center;
        color: #FFFFFF;
        font-size: 1.55rem;
        background: linear-gradient(135deg, #426CFF, #DA4BE8);
        margin-bottom: 16px;
    }
    .empty-title {
        color: #FFFFFF;
        font-weight: 790;
        font-size: 1.2rem;
        margin-bottom: 7px;
    }
    .empty-copy {
        color: #9EA4B1;
        max-width: 460px;
        line-height: 1.45;
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
    .face-card {
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 8px;
        padding: 12px;
        background: rgba(0, 0, 0, 0.32);
        margin-bottom: 10px;
        transition: border-color 160ms ease, background-color 160ms ease;
    }
    .face-card:hover {
        border-color: rgba(110, 168, 255, 0.35);
        background: rgba(255,255,255,0.045);
    }
    .face-card strong {
        color: #FFFFFF;
        letter-spacing: 1px;
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
    @media (max-width: 900px) {
        .studio-nav {
            align-items: flex-start;
            flex-direction: column;
            padding: 16px;
        }
        .nav-status {
            justify-content: flex-start;
        }
        .nav-user {
            max-width: 100%;
            text-align: left;
        }
        .flow-strip {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=10)
def load_api_config():
    try:
        response = requests.get(f"{API_URL}/config", timeout=5)
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


def auth_headers():
    token = st.session_state.get("auth_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def absolute_url(url):
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{API_URL}{url}"


def save_auth_session(auth_payload):
    token = auth_payload.get("access_token")
    user = auth_payload.get("user") or {}
    if token:
        st.session_state.auth_token = token
        st.session_state.auth_user = user
        st.sidebar.success(f"Signed in as {user.get('email') or 'user'}")
        st.rerun()
    else:
        st.sidebar.info(auth_payload.get("message", "Account created. Login may require email confirmation."))


def submit_auth(auth_mode, email, password, location):
    endpoint = "login" if auth_mode == "Login" else "signup"
    try:
        response = requests.post(
            f"{API_URL}/auth/{endpoint}",
            json={"email": email, "password": password},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        location.error(f"{auth_mode} failed: {exc}")
    else:
        auth_payload = response.json()
        token = auth_payload.get("access_token")
        user = auth_payload.get("user") or {}
        if token:
            st.session_state.auth_token = token
            st.session_state.auth_user = user
            st.rerun()
        else:
            location.info(auth_payload.get("message", "Account created. Login may require email confirmation."))


def handle_request_error(exc, location, action):
    message = str(exc)
    if "401" in message or "Unauthorized" in message:
        st.session_state.pop("auth_token", None)
        st.session_state.pop("auth_user", None)
        st.session_state.auth_notice = "Your login expired. Please sign in again, then continue."
        st.rerun()
    location.error(f"{action} failed: {exc}")


def render_login_page():
    st.write("")
    st.write("")
    left, middle, right = st.columns([1, 0.9, 1])
    with middle:
        st.markdown(
            """
            <div class="login-card">
                <div class="login-brand">AIFX Face Processing</div>
                <div class="login-subtitle">Sign in to upload images, crop faces, and keep your task history private in Supabase.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        auth_mode = st.radio("Account action", ["Login", "Sign up"], horizontal=True, label_visibility="collapsed")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Password")
        if st.session_state.get("auth_notice"):
            st.info(st.session_state.pop("auth_notice"))
        if st.button(auth_mode, type="primary", use_container_width=True):
            submit_auth(auth_mode, email, password, st)
        st.caption("Use a test password. This is an app user account, not your Supabase admin login.")


api_config = load_api_config()
supabase_enabled = api_config.get("supabase_enabled", False)

if not api_config.get("api_available"):
    st.error(f"Backend unavailable: {api_config.get('error')}")
    st.stop()

if supabase_enabled and not st.session_state.get("auth_token"):
    render_login_page()
    st.stop()

current_user = st.session_state.get("auth_user") or {}
nav_user = escape(current_user.get("email") or "Local workspace")
provider_label = escape(str(api_config.get("storage_provider", "unknown")).upper())
st.markdown(
    f"""
    <div class="studio-nav">
        <div class="brand-mark"><div class="brand-orb"></div><div>AIFX</div></div>
        <div class="nav-status">
            <span class="nav-chip hot">Face Crop Studio</span>
            <span class="nav-chip">Detect → Select → Save</span>
            <span class="nav-chip">{provider_label}</span>
        </div>
        <div class="nav-user">{nav_user}</div>
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


def init_control_state(name, default, minimum, maximum):
    value = clamp_value(st.session_state.get(name, default), minimum, maximum)
    st.session_state[name] = value


init_control_state("full_range_confidence", 0.10, 0.01, 0.99)
init_control_state("short_range_confidence", 0.23, 0.01, 0.99)
init_control_state("crop_scale", 2.2, 1.0, 5.0)
init_control_state("shoulder_bias", 0.2, -1.5, 1.5)

detection_range_labels = {
    "balanced": "Balanced full + short",
    "full_range": "Full range",
    "short_range": "Short range",
}
if st.session_state.get("detection_range") not in detection_range_labels:
    st.session_state.detection_range = "balanced"


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


st.sidebar.selectbox(
    "Detection range",
    options=list(detection_range_labels.keys()),
    key="detection_range",
    format_func=lambda value: detection_range_labels[value],
    help=(
        "Balanced runs both full-range and short-range models, then merges duplicate boxes. "
        "Full range is better for small distant faces. Short range is cleaner for close faces."
    ),
)
if st.session_state.detection_range in {"balanced", "full_range"}:
    linked_slider_number(
        "Full-range confidence",
        "full_range_confidence",
        0.01,
        0.99,
        sync_full_range_confidence_slider,
        sync_full_range_confidence_input,
        help_text=(
            "Controls the full-range model. Lower this first when distant or small faces are missing. "
            "Lower values may add face-like false positives."
        ),
    )
if st.session_state.detection_range in {"balanced", "short_range"}:
    linked_slider_number(
        "Short-range confidence",
        "short_range_confidence",
        0.01,
        0.99,
        sync_short_range_confidence_slider,
        sync_short_range_confidence_input,
        help_text=(
            "Controls the short-range model for close or large faces. Raise it if nearby faces create too many duplicates or false positives."
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
    st.session_state.pop("crop_result", None)
    st.session_state.pop("select_all_faces", None)
    for key in list(st.session_state.keys()):
        if str(key).startswith("select_face_"):
            st.session_state.pop(key, None)


def selected_face_indices(faces):
    return [
        face["face_index"]
        for face in faces
        if st.session_state.get(f"select_face_{face['face_index']}", False)
    ]


def workspace_stage(uploaded_file):
    if uploaded_file is None:
        return "upload"
    if st.session_state.get("crop_result"):
        return "output"
    if st.session_state.get("detection_result"):
        return "select"
    return "detect"


def render_flow(stage):
    steps = [
        ("upload", "01", "Upload Image", "Choose a JPG or PNG from your workspace."),
        ("detect", "02", "Detect Faces", "Find every candidate before saving crops."),
        ("select", "03", "Select & Crop", "Save only the faces you choose."),
    ]
    order = {"upload": 0, "detect": 1, "select": 2, "output": 2}
    active_index = order.get(stage, 0)
    html = ['<div class="flow-strip">']
    for index, (key, number, label, copy) in enumerate(steps):
        class_name = "flow-step active" if index == active_index else "flow-step"
        html.append(
            f'<div class="{class_name}">'
            f'<div class="flow-num">{number}</div>'
            f'<div class="flow-label">{label}</div>'
            f'<div class="flow-copy">{copy}</div>'
            "</div>"
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


tab_workspace, tab_history = st.tabs(["Workspace", "Task History"])

with tab_workspace:
    st.markdown(
        """
        <div class="studio-kicker">SUPADAWG · MULTI-FACE RECOGNITION V2.0</div>
        <div class="studio-title">AIFX <span>Studio</span></div>
        <div class="studio-subtitle">Detect every candidate face first, review the crop regions, then save only the faces you select.</div>
        """,
        unsafe_allow_html=True,
    )
    upload_col, action_col = st.columns([0.72, 0.28])
    with upload_col:
        uploaded_file = st.file_uploader("Upload Or Change Image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    with action_col:
        if st.button("Clear workspace", use_container_width=True):
            reset_detection_state()
            st.rerun()

    render_flow(workspace_stage(uploaded_file))

    if uploaded_file is None:
        empty_left, empty_right = st.columns([0.62, 0.38], gap="large")
        with empty_left:
            st.markdown(
                """
                <div class="empty-panel">
                    <div class="empty-icon">+</div>
                    <div class="empty-title">Start With A Group Photo</div>
                    <div class="empty-copy">Upload a JPG or PNG. The app will show candidate faces before creating any crop files.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with empty_right:
            st.markdown(
                """
                <div class="panel">
                    <div class="panel-title">What Happens Next</div>
                    <div class="flow-copy">1. Detect all candidate faces in the image.</div>
                    <div class="flow-copy">2. Review each face preview and crop coordinates.</div>
                    <div class="flow-copy">3. Select one or more faces and save only those crops.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        if st.session_state.get("uploaded_filename") != uploaded_file.name:
            reset_detection_state()
            st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.uploaded_image_bytes = image_bytes

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
                with st.spinner("Detecting candidate faces…"):
                    files = {
                        "file": (
                            uploaded_file.name,
                            image_bytes,
                            uploaded_file.type or "application/octet-stream",
                        )
                    }
                    data = {
                        "min_detection_confidence": min(
                            st.session_state.full_range_confidence,
                            st.session_state.short_range_confidence,
                        ),
                        "detection_range": st.session_state.detection_range,
                        "full_range_confidence": st.session_state.full_range_confidence,
                        "short_range_confidence": st.session_state.short_range_confidence,
                        "crop_scale": st.session_state.crop_scale,
                        "shoulder_bias": st.session_state.shoulder_bias,
                    }
                    try:
                        response = requests.post(
                            f"{API_URL}/detect-faces",
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

            detection_result = st.session_state.get("detection_result")
            if detection_result:
                metric_items = [
                    f"Task {detection_result['task_id'][:8]}",
                    f"{detection_result['face_count']} detected",
                    detection_range_labels.get(
                        detection_result.get("detection_range"),
                        detection_result.get("detection_range", "balanced"),
                    ),
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

                for face in faces:
                    face_bbox = face["face_bbox"]
                    crop_bbox = face["crop_bbox"]
                    st.markdown('<div class="face-card">', unsafe_allow_html=True)
                    preview_col, detail_col = st.columns([0.28, 0.72])
                    with preview_col:
                        st.image(
                            BytesIO(base64.b64decode(face["preview_base64"])),
                            caption=f"ID {face['face_index']}",
                            width="stretch",
                        )
                    with detail_col:
                        st.checkbox(
                            f"Face {face['face_index']} · confidence {face_bbox['confidence']:.2f}",
                            key=f"select_face_{face['face_index']}",
                        )
                        st.caption(
                            f"crop x={crop_bbox['x_min']} y={crop_bbox['y_min']} "
                            f"w={crop_bbox['width']} h={crop_bbox['height']}"
                        )
                        st.caption(
                            f"face x={face_bbox['x_min']} y={face_bbox['y_min']} "
                            f"w={face_bbox['width']} h={face_bbox['height']} "
                            f"model={face_bbox.get('model_range', 'unknown')}"
                        )
                    st.markdown("</div>", unsafe_allow_html=True)

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
                            response = requests.post(
                                f"{API_URL}/crop-selected",
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
                    for face in st.session_state.crop_result.get("faces", []):
                        st.markdown(
                            f"""
                            <div class="output-line">
                                <strong>{escape(face['filename'])}</strong><br>
                                {escape(absolute_url(face['url']))}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

with tab_history:
    try:
        response = requests.get(f"{API_URL}/tasks?limit=10", headers=auth_headers(), timeout=20)
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

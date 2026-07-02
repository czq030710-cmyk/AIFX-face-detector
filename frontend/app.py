import os
from io import BytesIO

from PIL import Image, ImageDraw
import requests
import streamlit as st
import streamlit.components.v1 as components


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


st.set_page_config(page_title="AIFX Face Processing", layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: #111318;
        border-right: 1px solid #2A2D35;
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

st.title("AIFX Face Processing")

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
    st.session_state.setdefault(f"{name}_slider", value)
    st.session_state.setdefault(f"{name}_input", value)


init_control_state("min_confidence", 0.23, 0.01, 0.99)
init_control_state("crop_scale", 2.2, 1.0, 5.0)
init_control_state("shoulder_bias", 0.2, -1.5, 1.5)


def sync_confidence_slider():
    value = clamp_value(st.session_state.min_confidence_slider, 0.01, 0.99)
    st.session_state.min_confidence = value
    st.session_state.min_confidence_input = value


def sync_confidence_input():
    value = clamp_value(st.session_state.min_confidence_input, 0.01, 0.99)
    st.session_state.min_confidence = value
    st.session_state.min_confidence_slider = value


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
):
    slider_col, input_col = st.sidebar.columns([0.68, 0.32])
    with slider_col:
        st.slider(
            label,
            min_value=minimum,
            max_value=maximum,
            value=st.session_state[state_name],
            step=0.01,
            key=f"{state_name}_slider",
            on_change=slider_callback,
            help=help_text,
        )
    with input_col:
        st.number_input(
            "Exact value",
            min_value=minimum,
            max_value=maximum,
            value=st.session_state[state_name],
            step=0.01,
            format="%.2f",
            key=f"{state_name}_input",
            on_change=input_callback,
            label_visibility="collapsed",
            help=help_text,
        )
    st.sidebar.caption(f"{label}: {st.session_state[state_name]:.2f}{suffix}")


linked_slider_number(
    "Confidence threshold",
    "min_confidence",
    0.01,
    0.99,
    sync_confidence_slider,
    sync_confidence_input,
    help_text=(
        "Controls how strict face detection is. Lower values can find smaller or harder faces, "
        "but may add false detections. Higher values are cleaner but may miss faces."
    ),
)
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
            f"face {face_bbox['confidence']:.2f}"
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

tab_workspace, tab_history = st.tabs(["Workspace", "Task History"])

with tab_workspace:
    uploaded_file = st.file_uploader("Upload a JPG or PNG image", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        st.image(image_bytes, caption="Original image", width="stretch")

        if st.button("Detect faces", type="primary"):
            with st.spinner("Detecting faces..."):
                files = {
                    "file": (
                        uploaded_file.name,
                        image_bytes,
                        uploaded_file.type or "application/octet-stream",
                    )
                }
                data = {
                    "min_detection_confidence": st.session_state.min_confidence,
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
                    st.error(f"Detection request failed: {exc}")
                else:
                    result = response.json()
                    st.success(result["message"])
                    st.json(
                        {
                            "task_id": result["task_id"],
                            "filename": result["filename"],
                            "user_id": result["user_id"],
                            "storage_provider": result["storage_provider"],
                            "original_image_url": result["original_image_url"],
                            "cropped_image_urls": result["cropped_image_urls"],
                            "min_detection_confidence": result["min_detection_confidence"],
                            "crop_scale": result["crop_scale"],
                            "shoulder_bias": result["shoulder_bias"],
                            "image_width": result["image_width"],
                            "image_height": result["image_height"],
                            "face_count": result["face_count"],
                        }
                    )

                    if result["faces"]:
                        overlay = draw_detection_overlay(image_bytes, result["faces"])
                        st.subheader("Detected locations on original image")
                        st.image(overlay, caption="Green boxes show the regions used for cropping.", width="stretch")

                        st.subheader("Detection metadata")
                        st.caption("Cropped face files are saved locally, but hidden here to keep the workspace focused.")
                        for face in result["faces"]:
                            with st.expander(f"Face {face['face_index']} metadata", expanded=True):
                                st.json({"face_bbox": face["face_bbox"], "crop_bbox": face["crop_bbox"]})
                                st.caption(f"Saved crop URL: {absolute_url(face['url'])}")

with tab_history:
    try:
        response = requests.get(f"{API_URL}/tasks?limit=10", headers=auth_headers(), timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        st.error(f"Could not load task history: {exc}")
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

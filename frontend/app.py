import os
import base64
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
    .stApp {
        background:
            radial-gradient(circle at 50% 8%, rgba(102, 69, 255, 0.18), transparent 34%),
            radial-gradient(circle at 8% 90%, rgba(24, 169, 255, 0.14), transparent 30%),
            #07080D;
        color: #F7F8FA;
    }
    .studio-nav {
        margin: 18px auto 26px;
        max-width: 1320px;
        min-height: 64px;
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 8px;
        background: rgba(8, 9, 14, 0.86);
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.45);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 22px;
    }
    .brand-mark {
        display: flex;
        align-items: center;
        gap: 14px;
        color: #FFFFFF;
        font-weight: 780;
        letter-spacing: 6px;
        font-size: 1.05rem;
    }
    .brand-orb {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3D7BFF, #E84CCB);
        border: 2px solid rgba(255, 255, 255, 0.72);
    }
    .nav-links {
        display: flex;
        gap: 38px;
        color: #777B86;
        font-size: 0.82rem;
        font-weight: 780;
        letter-spacing: 4px;
        text-transform: uppercase;
    }
    .nav-user {
        color: #DDE3EF;
        font-weight: 700;
        max-width: 260px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
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
        font-size: 2.1rem;
        line-height: 1.05;
        font-weight: 820;
        letter-spacing: 0;
        margin-bottom: 6px;
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
    }
    .face-card {
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 8px;
        padding: 12px;
        background: rgba(0, 0, 0, 0.32);
        margin-bottom: 10px;
    }
    .face-card strong {
        color: #FFFFFF;
        letter-spacing: 1px;
    }
    .muted {
        color: #9399A6;
        font-size: 0.86rem;
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
nav_user = current_user.get("email") or "Local workspace"
st.markdown(
    f"""
    <div class="studio-nav">
        <div class="brand-mark"><div class="brand-orb"></div><div>AIFX</div></div>
        <div class="nav-links"><span>News</span><span>Featured</span><span>Products</span><span>InsDawg</span><span>Crew</span></div>
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

def reset_detection_state():
    st.session_state.pop("detection_result", None)
    st.session_state.pop("uploaded_image_bytes", None)
    st.session_state.pop("uploaded_filename", None)


def selected_face_indices(faces):
    return [
        face["face_index"]
        for face in faces
        if st.session_state.get(f"select_face_{face['face_index']}", False)
    ]


tab_workspace, tab_history = st.tabs(["Workspace", "Task History"])

with tab_workspace:
    st.markdown(
        """
        <div class="studio-kicker">SUPADAWG · MULTI-FACE RECOGNITION V2.0</div>
        <div class="studio-title">AIFX <span>Studio</span></div>
        <div class="studio-subtitle">Detect every candidate face first, then choose exactly which faces become saved crop outputs.</div>
        """,
        unsafe_allow_html=True,
    )
    upload_col, action_col = st.columns([0.72, 0.28])
    with upload_col:
        uploaded_file = st.file_uploader("Change image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    with action_col:
        if st.button("Clear workspace", use_container_width=True):
            reset_detection_state()
            st.rerun()

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

            if st.button("Detect All Faces", type="primary", use_container_width=True):
                with st.spinner("Detecting candidate faces..."):
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
                        handle_request_error(exc, st, "Detection request")
                    else:
                        st.session_state.detection_result = response.json()
                        for key in list(st.session_state.keys()):
                            if str(key).startswith("select_face_"):
                                st.session_state.pop(key, None)
                        st.rerun()

            detection_result = st.session_state.get("detection_result")
            if detection_result:
                st.markdown(
                    f"""
                    <div class="metric-row">
                        <div class="metric-pill">Task {detection_result['task_id'][:8]}</div>
                        <div class="metric-pill">{detection_result['face_count']} detected</div>
                        <div class="metric-pill">{detection_result['image_width']} x {detection_result['image_height']}</div>
                        <div class="metric-pill">{detection_result['storage_provider']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with right_panel:
            st.markdown('<div class="panel-title">Detected Faces</div>', unsafe_allow_html=True)
            detection_result = st.session_state.get("detection_result")
            if not detection_result:
                st.info("Upload an image and run detection. Face candidates will appear here before any crop files are saved.")
            elif not detection_result.get("faces"):
                st.warning("No faces detected. Try lowering the confidence threshold or increasing crop expansion.")
            else:
                faces = detection_result["faces"]
                select_all = st.checkbox("Select all detected faces", value=False)
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
                            f"w={face_bbox['width']} h={face_bbox['height']}"
                        )
                    st.markdown("</div>", unsafe_allow_html=True)

                selected_indices = selected_face_indices(faces)
                st.caption(f"{len(selected_indices)} selected for output.")
                if st.button("Start the Magic", type="primary", use_container_width=True, disabled=not selected_indices):
                    with st.spinner("Cropping and saving selected faces..."):
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
                            st.json(
                                {
                                    "task_id": crop_result["task_id"],
                                    "selected_face_indices": selected_indices,
                                    "cropped_image_urls": crop_result["cropped_image_urls"],
                                }
                            )
                if st.session_state.get("crop_result"):
                    st.markdown('<div class="panel-title">Saved Output</div>', unsafe_allow_html=True)
                    for face in st.session_state.crop_result.get("faces", []):
                        st.caption(f"{face['filename']} · {absolute_url(face['url'])}")

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

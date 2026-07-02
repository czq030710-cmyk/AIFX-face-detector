import os
from io import BytesIO

from PIL import Image, ImageDraw
import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


st.set_page_config(page_title="AIFX Face Processing", layout="wide")
st.title("AIFX Face Processing")


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


api_config = load_api_config()
supabase_enabled = api_config.get("supabase_enabled", False)

st.sidebar.header("Session")
if not api_config.get("api_available"):
    st.sidebar.error(f"Backend unavailable: {api_config.get('error')}")
elif supabase_enabled:
    if st.session_state.get("auth_token"):
        user = st.session_state.get("auth_user") or {}
        st.sidebar.success(f"Signed in as {user.get('email') or 'user'}")
        if st.sidebar.button("Sign out"):
            st.session_state.pop("auth_token", None)
            st.session_state.pop("auth_user", None)
            st.rerun()
    else:
        auth_mode = st.sidebar.radio("Auth mode", ["Login", "Sign up"], horizontal=True)
        with st.sidebar.form("auth_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(auth_mode)
        if submitted:
            endpoint = "login" if auth_mode == "Login" else "signup"
            try:
                response = requests.post(
                    f"{API_URL}/auth/{endpoint}",
                    json={"email": email, "password": password},
                    timeout=20,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                st.sidebar.error(f"{auth_mode} failed: {exc}")
            else:
                save_auth_session(response.json())
else:
    st.sidebar.info("Local demo mode. Add Supabase values in `.env` to enable login, cloud storage, and user-isolated history.")

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

        if supabase_enabled and not st.session_state.get("auth_token"):
            st.warning("Please log in before uploading to Supabase storage and task history.")
        elif st.button("Detect faces", type="primary"):
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
    if supabase_enabled and not st.session_state.get("auth_token"):
        st.info("Log in to view your user-isolated task history.")
    else:
        try:
            response = requests.get(f"{API_URL}/tasks", headers=auth_headers(), timeout=20)
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

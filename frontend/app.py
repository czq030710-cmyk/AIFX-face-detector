import os
from io import BytesIO

from PIL import Image, ImageDraw
import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


st.set_page_config(page_title="AIFX Face Processing", layout="wide")
st.title("AIFX Face Processing")

st.sidebar.header("Session")
st.sidebar.info("Local prototype mode. Supabase Auth will be added in the next phase.")
st.sidebar.header("Detection Controls")
st.sidebar.caption("Lower values find more small/side faces, but may add false positives.")


def clamp_value(value, minimum, maximum):
    return min(maximum, max(minimum, round(float(value), 2)))


def init_control_state(name, default, minimum, maximum):
    value = clamp_value(st.session_state.get(name, default), minimum, maximum)
    st.session_state[name] = value
    st.session_state.setdefault(f"{name}_slider", value)
    st.session_state.setdefault(f"{name}_input", value)


init_control_state("min_confidence", 0.5, 0.01, 0.99)
init_control_state("crop_scale", 3.0, 1.0, 5.0)
init_control_state("shoulder_bias", 0.4, -1.5, 1.5)


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
                    response = requests.post(f"{API_URL}/detect-faces", files=files, data=data, timeout=60)
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
                                st.caption(f"Saved crop URL: {API_URL}{face['url']}")

with tab_history:
    st.info("Task history will be connected after Supabase Auth, Database, and Storage are added.")

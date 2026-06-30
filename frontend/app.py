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

st.session_state.min_confidence = min(
    0.9,
    max(0.1, round(st.session_state.get("min_confidence", 0.5), 1)),
)


def sync_confidence_slider():
    st.session_state.min_confidence = st.session_state.confidence_slider


def sync_confidence_input():
    st.session_state.min_confidence = st.session_state.confidence_input


st.sidebar.slider(
    "Confidence threshold",
    min_value=0.1,
    max_value=0.9,
    value=st.session_state.min_confidence,
    step=0.1,
    key="confidence_slider",
    on_change=sync_confidence_slider,
)
st.sidebar.number_input(
    "Manual threshold",
    min_value=0.1,
    max_value=0.9,
    value=st.session_state.min_confidence,
    step=0.1,
    format="%.1f",
    key="confidence_input",
    on_change=sync_confidence_input,
)
st.sidebar.metric("Current threshold", f"{st.session_state.min_confidence:.1f}")


def draw_detection_overlay(image_bytes, faces):
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    line_width = max(3, int(max(image.size) / 260))

    for face in faces:
        bbox = face["bbox"]
        x_min = int(bbox["x_min"])
        y_min = int(bbox["y_min"])
        x_max = x_min + int(bbox["width"])
        y_max = y_min + int(bbox["height"])
        label = (
            f"Face {face['face_index']} | "
            f"x={x_min} y={y_min} w={int(bbox['width'])} h={int(bbox['height'])} | "
            f"{bbox['confidence']:.2f}"
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
                data = {"min_detection_confidence": st.session_state.min_confidence}
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
                                st.json(face["bbox"])
                                st.caption(f"Saved crop URL: {API_URL}{face['url']}")

with tab_history:
    st.info("Task history will be connected after Supabase Auth, Database, and Storage are added.")

import base64
import os

import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


st.set_page_config(page_title="AIFX Face Processing", layout="wide")
st.title("AIFX Face Processing")

st.sidebar.header("Session")
st.sidebar.info("Local prototype mode. Supabase Auth will be added in the next phase.")
st.sidebar.header("Detection Controls")
st.sidebar.caption("Lower values find more small/side faces, but may add false positives.")

if "min_confidence" not in st.session_state:
    st.session_state.min_confidence = 0.5


def sync_confidence_slider():
    st.session_state.min_confidence = st.session_state.confidence_slider


def sync_confidence_input():
    st.session_state.min_confidence = st.session_state.confidence_input


st.sidebar.slider(
    "Confidence threshold",
    min_value=0.05,
    max_value=0.95,
    value=st.session_state.min_confidence,
    step=0.05,
    key="confidence_slider",
    on_change=sync_confidence_slider,
)
st.sidebar.number_input(
    "Manual threshold",
    min_value=0.05,
    max_value=0.95,
    value=st.session_state.min_confidence,
    step=0.01,
    format="%.2f",
    key="confidence_input",
    on_change=sync_confidence_input,
)
st.sidebar.metric("Current threshold", f"{st.session_state.min_confidence:.2f}")

tab_workspace, tab_history = st.tabs(["Workspace", "Task History"])

with tab_workspace:
    uploaded_file = st.file_uploader("Upload a JPG or PNG image", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        st.image(image_bytes, caption="Original image", use_container_width=True)

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
                        columns = st.columns(min(result["face_count"], 3))
                        for index, face in enumerate(result["faces"]):
                            image_data = base64.b64decode(face["preview_base64"])
                            with columns[index % len(columns)]:
                                st.image(image_data, caption=f"Face {face['face_index']}", use_container_width=True)
                                st.json(face["bbox"])
                                st.caption(f"Local URL: {API_URL}{face['url']}")

with tab_history:
    st.info("Task history will be connected after Supabase Auth, Database, and Storage are added.")

from base64 import b64encode
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import re
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from backend.comfyui_client import ComfyUIClient, ComfyUIError
from core_ai.face_detector import FaceDetector
from backend.supabase_client import SupabaseGateway, UserContext


app = FastAPI(title="AIFX Phase 1 Face Processing API")
DETECTORS = {
    "short_range": FaceDetector(model_range="short_range"),
    "full_range": FaceDetector(model_range="full_range"),
}
TILE_SCAN_ENABLED = True
TILE_SCAN_GRID = "2x2"
TILE_SCAN_TILE_RATIO = 0.62
TILE_SCAN_MIN_SIDE = 900
supabase_gateway = SupabaseGateway()

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
ORIGINALS_DIR = STORAGE_DIR / "originals"
CROPS_DIR = STORAGE_DIR / "crops"
DETECTIONS_DIR = STORAGE_DIR / "detections"
ENHANCED_DIR = STORAGE_DIR / "enhanced"
LOCAL_HISTORY_PATH = STORAGE_DIR / "task_history.json"
WORKFLOW_TEMPLATE_PATH = Path(__file__).resolve().parent / "workflows" / "zooey.json"
LORA_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "lora_config.json"
COMFY_OUTPUT_NODE_ID = "866"
for directory in (ORIGINALS_DIR, CROPS_DIR, DETECTIONS_DIR, ENHANCED_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")


class AuthCredentials(BaseModel):
    email: str
    password: str


class CropSelectionRequest(BaseModel):
    task_id: str
    selected_face_indices: list[int]


def get_current_user(authorization: str | None = Header(default=None)) -> UserContext:
    return supabase_gateway.get_user_from_authorization(authorization)


def get_phase2_user(authorization: str | None = Header(default=None)) -> UserContext:
    configured_keys = [
        key.strip()
        for key in os.getenv("AIFX_PHASE2_API_KEYS", "").split(",")
        if key.strip()
    ]
    if not configured_keys:
        return get_current_user(authorization)

    token = bearer_token(authorization)
    if token not in configured_keys:
        raise HTTPException(status_code=401, detail="Invalid Phase 2 API key.")
    return UserContext(
        user_id="phase2-api-key",
        email=None,
        access_token=token,
        is_authenticated=True,
    )


def bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header must use Bearer token.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Authorization header must use Bearer token.")
    return token.strip()


def safe_filename_stem(filename: str | None) -> str:
    stem = Path(filename or "upload").stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._")
    return (stem or "upload")[:80]


def load_json_file(path: Path) -> dict:
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Missing required file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON file: {path}") from exc


def load_lora_config() -> dict:
    config = load_json_file(LORA_CONFIG_PATH)
    if "characters" not in config or not isinstance(config["characters"], dict):
        raise HTTPException(status_code=500, detail="lora_config.json must include a characters object.")
    if "default_character_id" not in config:
        raise HTTPException(status_code=500, detail="lora_config.json must include default_character_id.")
    return config


def resolve_character_lora(character_id: str | None) -> dict:
    config = load_lora_config()
    resolved_character_id = (character_id or config["default_character_id"]).strip()
    character = config["characters"].get(resolved_character_id)
    if not character:
        known_characters = ", ".join(sorted(config["characters"].keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown character_id '{resolved_character_id}'. Known characters: {known_characters}",
        )
    lora_name = character.get("lora_name")
    if not lora_name:
        raise HTTPException(status_code=500, detail=f"Missing lora_name for character_id '{resolved_character_id}'.")
    return {
        "character_id": resolved_character_id,
        "lora_name": lora_name,
        "display_name": character.get("display_name", resolved_character_id),
    }


def build_comfyui_workflow(
    uploaded_image_filename: str,
    lora_name: str,
    prompt: str,
    job_id: str,
) -> dict:
    workflow = deepcopy(load_json_file(WORKFLOW_TEMPLATE_PATH))
    required_nodes = {
        "958": "LoadImage source image",
        "1056": "first pass LoRA",
        "1057": "second pass LoRA",
        "1071": "manual prompt",
        COMFY_OUTPUT_NODE_ID: "SaveImage output",
    }
    missing_nodes = [
        f"{node_id} ({label})"
        for node_id, label in required_nodes.items()
        if node_id not in workflow
    ]
    if missing_nodes:
        raise HTTPException(status_code=500, detail=f"Workflow template is missing nodes: {missing_nodes}")

    workflow["958"]["inputs"]["image"] = uploaded_image_filename
    workflow["1056"]["inputs"]["lora_name"] = lora_name
    workflow["1057"]["inputs"]["lora_name"] = lora_name
    workflow["1071"]["inputs"]["text"] = prompt.strip()
    workflow[COMFY_OUTPUT_NODE_ID]["inputs"]["filename_prefix"] = f"phase2/{job_id}"
    return workflow


def workflow_injection_summary(workflow: dict) -> dict:
    return {
        "958.inputs.image": workflow["958"]["inputs"]["image"],
        "1056.inputs.lora_name": workflow["1056"]["inputs"]["lora_name"],
        "1057.inputs.lora_name": workflow["1057"]["inputs"]["lora_name"],
        "1071.inputs.text": workflow["1071"]["inputs"]["text"],
        f"{COMFY_OUTPUT_NODE_ID}.inputs.filename_prefix": workflow[COMFY_OUTPUT_NODE_ID]["inputs"]["filename_prefix"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "aifx-face-processing-api"}


@app.get("/config")
def get_config():
    return {
        "supabase_enabled": supabase_gateway.enabled,
        "storage_provider": "supabase" if supabase_gateway.enabled else "local",
    }


@app.get("/api/v1/face-enhance/config")
def get_face_enhance_config(user: UserContext = Depends(get_phase2_user)):
    lora_config = load_lora_config()
    return {
        "workflow_template": str(WORKFLOW_TEMPLATE_PATH.relative_to(Path(__file__).resolve().parent.parent)),
        "required_nodes": ["958", "1056", "1057", "1071", COMFY_OUTPUT_NODE_ID],
        "comfyui_url": os.getenv("COMFYUI_URL", "http://127.0.0.1:8188"),
        "default_character_id": lora_config["default_character_id"],
        "characters": sorted(lora_config["characters"].keys()),
        "user_id": user.user_id,
    }


@app.post("/api/v1/face-enhance")
async def enhance_face_crop(
    image: UploadFile = File(...),
    character_id: str | None = Form(None),
    prompt: str = Form(""),
    dry_run: bool = Form(False),
    user: UserContext = Depends(get_phase2_user),
):
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Only .jpg and .png images are supported.")

    image_bytes = await image.read()
    try:
        source_image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.") from exc

    png_buffer = BytesIO()
    source_image.save(png_buffer, format="PNG")
    upload_bytes = png_buffer.getvalue()

    job_id = f"req_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    upload_filename = f"{job_id}_{safe_filename_stem(image.filename)}.png"
    resolved_lora = resolve_character_lora(character_id)
    injected_workflow = build_comfyui_workflow(
        uploaded_image_filename=upload_filename,
        lora_name=resolved_lora["lora_name"],
        prompt=prompt,
        job_id=job_id,
    )

    if dry_run:
        return {
            "job_id": job_id,
            "status": "dry_run_ready",
            "message": "Workflow template injection succeeded. ComfyUI was not called.",
            "metadata": {
                "workflow_template": "zooey.json",
                "character_id": resolved_lora["character_id"],
                "lora_name": resolved_lora["lora_name"],
                "uploaded_image_filename": upload_filename,
                "output_node_id": COMFY_OUTPUT_NODE_ID,
                "injected_nodes": workflow_injection_summary(injected_workflow),
            },
        }

    comfyui_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    comfyui_timeout = int(os.getenv("COMFYUI_TIMEOUT_SECONDS", "300"))
    client = ComfyUIClient(comfyui_url, timeout_seconds=comfyui_timeout)
    started_at = time.monotonic()

    try:
        comfyui_image_name = client.upload_image(upload_bytes, upload_filename)
        injected_workflow = build_comfyui_workflow(
            uploaded_image_filename=comfyui_image_name,
            lora_name=resolved_lora["lora_name"],
            prompt=prompt,
            job_id=job_id,
        )
        prompt_id = client.submit_prompt(injected_workflow)
        output_image = client.wait_for_output(prompt_id, COMFY_OUTPUT_NODE_ID)
        enhanced_bytes = client.fetch_image(output_image)
    except ComfyUIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    enhanced_filename = f"{job_id}-enhanced-crop.png"
    enhanced_path = ENHANCED_DIR / enhanced_filename
    enhanced_path.write_bytes(enhanced_bytes)
    runtime_seconds = round(time.monotonic() - started_at, 2)

    return {
        "job_id": job_id,
        "status": "completed",
        "enhanced_crop_url": f"/storage/enhanced/{enhanced_filename}",
        "metadata": {
            "workflow_template": "zooey.json",
            "comfyui_url": comfyui_url,
            "comfyui_prompt_id": prompt_id,
            "comfyui_output": {
                "filename": output_image.filename,
                "subfolder": output_image.subfolder,
                "type": output_image.image_type,
            },
            "character_id": resolved_lora["character_id"],
            "lora_name": resolved_lora["lora_name"],
            "uploaded_image_filename": comfyui_image_name,
            "output_node_id": COMFY_OUTPUT_NODE_ID,
            "runtime_seconds": runtime_seconds,
            "user_id": user.user_id,
        },
    }


@app.post("/auth/signup")
def sign_up(credentials: AuthCredentials):
    return supabase_gateway.sign_up(credentials.email, credentials.password)


@app.post("/auth/login")
def sign_in(credentials: AuthCredentials):
    return supabase_gateway.sign_in(credentials.email, credentials.password)


@app.get("/tasks")
def list_tasks(
    limit: int = Query(default=10, ge=1, le=10),
    user: UserContext = Depends(get_current_user),
):
    if supabase_gateway.enabled:
        tasks = supabase_gateway.list_tasks(user, limit)
    else:
        tasks = read_local_history(limit)
    return {
        "storage_provider": "supabase" if supabase_gateway.enabled else "local",
        "user_id": user.user_id,
        "tasks": tasks,
    }


@app.post("/detect-faces")
async def detect_faces(
    file: UploadFile = File(...),
    min_detection_confidence: float = Form(0.23),
    detection_range: str = Form("balanced"),
    full_range_confidence: float | None = Form(None),
    short_range_confidence: float | None = Form(None),
    crop_scale: float = Form(2.2),
    shoulder_bias: float = Form(0.2),
    user: UserContext = Depends(get_current_user),
):
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Only .jpg and .png images are supported.")
    if not 0.0 <= min_detection_confidence <= 1.0:
        raise HTTPException(status_code=400, detail="min_detection_confidence must be between 0.0 and 1.0.")
    if full_range_confidence is not None and not 0.0 <= full_range_confidence <= 1.0:
        raise HTTPException(status_code=400, detail="full_range_confidence must be between 0.0 and 1.0.")
    if short_range_confidence is not None and not 0.0 <= short_range_confidence <= 1.0:
        raise HTTPException(status_code=400, detail="short_range_confidence must be between 0.0 and 1.0.")
    if detection_range not in {"short_range", "full_range", "balanced"}:
        raise HTTPException(
            status_code=400,
            detail="detection_range must be short_range, full_range, or balanced.",
        )
    if not 1.0 <= crop_scale <= 5.0:
        raise HTTPException(status_code=400, detail="crop_scale must be between 1.0 and 5.0.")
    if not -1.5 <= shoulder_bias <= 1.5:
        raise HTTPException(status_code=400, detail="shoulder_bias must be between -1.5 and 1.5.")

    image_bytes = await file.read()
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.") from exc

    task_id = str(uuid4())
    short_task_id = task_id.split("-")[0]
    source_stem = safe_filename_stem(file.filename)
    original_extension = ".jpg" if file.content_type == "image/jpeg" else ".png"
    original_filename = f"{source_stem}-original-{short_task_id}{original_extension}"
    original_path = ORIGINALS_DIR / original_filename
    original_buffer = BytesIO()
    image.save(original_buffer, format="JPEG" if original_extension == ".jpg" else "PNG")
    original_bytes = original_buffer.getvalue()
    original_path.write_bytes(original_bytes)
    original_image_url = f"/storage/originals/{original_filename}"
    storage_provider = "supabase" if supabase_gateway.enabled else "local"
    if supabase_gateway.enabled:
        original_image_url = supabase_gateway.upload_bytes(
            f"{user.user_id}/{task_id}/originals/{original_filename}",
            original_bytes,
            file.content_type,
        )

    detection_thresholds = resolve_detection_thresholds(
        min_detection_confidence=min_detection_confidence,
        full_range_confidence=full_range_confidence,
        short_range_confidence=short_range_confidence,
    )
    faces = detect_faces_by_range(image, detection_range, detection_thresholds)
    detected_faces = []
    bounding_boxes = []

    face_candidates = []
    for detected_index, face in enumerate(faces):
        x = face["x"]
        y = face["y"]
        width = face["width"]
        height = face["height"]
        if not is_plausible_detected_face(face, image.width, image.height):
            continue
        crop_bbox = expand_face_bbox(
            x=x,
            y=y,
            width=width,
            height=height,
            image_width=image.width,
            image_height=image.height,
            crop_scale=crop_scale,
            shoulder_bias=shoulder_bias,
        )
        face_bbox = {
            "detected_index": detected_index,
            "x_min": x,
            "y_min": y,
            "width": width,
            "height": height,
            "confidence": face["score"],
            "model_range": face["model_range"],
            "image_width": image.width,
            "image_height": image.height,
        }
        face_candidates.append(
            {
                "face": face,
                "face_bbox": face_bbox,
                "crop_bbox": crop_bbox,
            }
        )

    filtered_faces = filter_face_candidates(face_candidates)

    for face_index, candidate in enumerate(filtered_faces):
        crop_bbox = candidate["crop_bbox"]
        face_bbox = {**candidate["face_bbox"], "face_index": face_index}
        face_bbox.pop("detected_index", None)
        bounding_box = {
            "face_index": face_index,
            "face_bbox": face_bbox,
            "crop_bbox": crop_bbox,
        }
        bounding_boxes.append(bounding_box)
        detected_faces.append(
            {
                "face_index": face_index,
                "bbox": crop_bbox,
                "face_bbox": face_bbox,
                "crop_bbox": crop_bbox,
                "preview_base64": preview_crop_base64(image, crop_bbox),
            }
        )

    pending_detection = {
        "task_id": task_id,
        "filename": file.filename,
        "source_stem": source_stem,
        "short_task_id": short_task_id,
        "original_filename": original_filename,
        "original_path": str(original_path),
        "original_image_url": original_image_url,
        "original_content_type": file.content_type,
        "user_id": user.user_id,
        "storage_provider": storage_provider,
        "image_width": image.width,
        "image_height": image.height,
        "settings": {
            "min_detection_confidence": min_detection_confidence,
            "detection_range": detection_range,
            "full_range_confidence": detection_thresholds["full_range"],
            "short_range_confidence": detection_thresholds["short_range"],
            "tile_scan_enabled": detection_range == "balanced" and should_run_tile_scan(image),
            "tile_scan_grid": TILE_SCAN_GRID,
            "tile_scan_tile_ratio": TILE_SCAN_TILE_RATIO,
            "crop_scale": crop_scale,
            "shoulder_bias": shoulder_bias,
        },
        "faces": [
            {
                "face_index": face["face_index"],
                "face_bbox": face["face_bbox"],
                "crop_bbox": face["crop_bbox"],
            }
            for face in detected_faces
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_pending_detection(pending_detection)

    response_payload = {
        "task_id": task_id,
        "status": "detected",
        "filename": file.filename,
        "user_id": user.user_id,
        "storage_provider": storage_provider,
        "original_image_url": original_image_url,
        "cropped_image_urls": [],
        "bounding_boxes": bounding_boxes,
        "min_detection_confidence": min_detection_confidence,
        "detection_range": detection_range,
        "full_range_confidence": detection_thresholds["full_range"],
        "short_range_confidence": detection_thresholds["short_range"],
        "tile_scan_enabled": detection_range == "balanced" and should_run_tile_scan(image),
        "tile_scan_grid": TILE_SCAN_GRID,
        "crop_scale": crop_scale,
        "shoulder_bias": shoulder_bias,
        "image_width": image.width,
        "image_height": image.height,
        "face_count": len(detected_faces),
        "faces": detected_faces,
        "message": "No faces detected." if not detected_faces else "Faces detected. Select faces to crop.",
    }
    return response_payload


@app.post("/crop-selected")
def crop_selected_faces(
    selection: CropSelectionRequest,
    user: UserContext = Depends(get_current_user),
):
    pending_detection = read_pending_detection(selection.task_id)
    if pending_detection["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="This detection task belongs to another user.")

    selected_indices = []
    for face_index in selection.selected_face_indices:
        if face_index not in selected_indices:
            selected_indices.append(face_index)
    if not selected_indices:
        raise HTTPException(status_code=400, detail="Select at least one face to crop.")

    faces_by_index = {
        face["face_index"]: face
        for face in pending_detection.get("faces", [])
    }
    missing_indices = [
        face_index
        for face_index in selected_indices
        if face_index not in faces_by_index
    ]
    if missing_indices:
        raise HTTPException(status_code=400, detail=f"Unknown face index: {missing_indices}")

    original_path = Path(pending_detection["original_path"])
    if not original_path.exists():
        raise HTTPException(status_code=404, detail="Original image for this detection is no longer available.")

    image = Image.open(original_path).convert("RGB")
    task_id = pending_detection["task_id"]
    source_stem = pending_detection["source_stem"]
    short_task_id = pending_detection["short_task_id"]
    cropped_faces = []
    cropped_image_urls = []
    bounding_boxes = []

    for output_index, face_index in enumerate(selected_indices, start=1):
        face = faces_by_index[face_index]
        crop_bbox = face["crop_bbox"]
        crop = image.crop(
            (
                crop_bbox["x_min"],
                crop_bbox["y_min"],
                crop_bbox["x_min"] + crop_bbox["width"],
                crop_bbox["y_min"] + crop_bbox["height"],
            )
        )

        buffer = BytesIO()
        crop.save(buffer, format="PNG")
        crop_bytes = buffer.getvalue()
        crop_filename = f"{source_stem}-crops-{output_index:02d}-{short_task_id}.png"
        crop_path = CROPS_DIR / crop_filename
        crop_path.write_bytes(crop_bytes)

        crop_url = f"/storage/crops/{crop_filename}"
        if supabase_gateway.enabled:
            crop_url = supabase_gateway.upload_bytes(
                f"{user.user_id}/{task_id}/crops/{crop_filename}",
                crop_bytes,
                "image/png",
            )
        cropped_image_urls.append(crop_url)

        bounding_box = {
            "face_index": face_index,
            "output_index": output_index,
            "face_bbox": face["face_bbox"],
            "crop_bbox": crop_bbox,
        }
        bounding_boxes.append(bounding_box)
        cropped_faces.append(
            {
                "face_index": face_index,
                "output_index": output_index,
                "filename": crop_filename,
                "url": crop_url,
                "bbox": crop_bbox,
                "face_bbox": face["face_bbox"],
                "crop_bbox": crop_bbox,
                "preview_base64": b64encode(crop_bytes).decode("ascii"),
            }
        )

    task_record = {
        "task_id": task_id,
        "user_id": user.user_id,
        "filename": pending_detection["filename"],
        "status": "completed",
        "original_image_url": pending_detection["original_image_url"],
        "cropped_image_urls": cropped_image_urls,
        "bounding_boxes": bounding_boxes,
        "face_count": len(cropped_faces),
        "image_width": pending_detection["image_width"],
        "image_height": pending_detection["image_height"],
        "settings": {
            **pending_detection["settings"],
            "selected_face_indices": selected_indices,
            "detected_face_count": len(pending_detection.get("faces", [])),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_task_history(task_record)
    return {
        **task_record,
        "storage_provider": pending_detection["storage_provider"],
        "faces": cropped_faces,
        "message": f"Cropped {len(cropped_faces)} selected face(s).",
    }


def preview_crop_base64(image: Image.Image, crop_bbox: dict) -> str:
    crop = image.crop(
        (
            crop_bbox["x_min"],
            crop_bbox["y_min"],
            crop_bbox["x_min"] + crop_bbox["width"],
            crop_bbox["y_min"] + crop_bbox["height"],
        )
    )
    buffer = BytesIO()
    crop.save(buffer, format="PNG")
    return b64encode(buffer.getvalue()).decode("ascii")


def resolve_detection_thresholds(
    min_detection_confidence: float,
    full_range_confidence: float | None,
    short_range_confidence: float | None,
):
    return {
        "full_range": full_range_confidence if full_range_confidence is not None else min_detection_confidence,
        "short_range": short_range_confidence if short_range_confidence is not None else min_detection_confidence,
    }


def detect_faces_by_range(
    image: Image.Image,
    detection_range: str,
    detection_thresholds: dict,
):
    if detection_range == "balanced":
        model_ranges = ("short_range", "full_range")
    else:
        model_ranges = (detection_range,)

    faces = []
    for model_range in model_ranges:
        model_detector = DETECTORS[model_range]
        model_detector.min_detection_confidence = detection_thresholds[model_range]
        for face in model_detector.detect_faces(image):
            faces.append({**face, "model_range": model_range})

    if detection_range == "balanced" and should_run_tile_scan(image):
        faces.extend(detect_faces_with_tile_scan(image, detection_thresholds["full_range"]))
    return faces


def should_run_tile_scan(image: Image.Image):
    return TILE_SCAN_ENABLED and min(image.width, image.height) >= TILE_SCAN_MIN_SIDE


def detect_faces_with_tile_scan(image: Image.Image, min_detection_confidence: float):
    detector = DETECTORS["full_range"]
    previous_confidence = detector.min_detection_confidence
    detector.min_detection_confidence = min_detection_confidence
    faces = []
    try:
        for tile_index, (tile_x, tile_y, tile_width, tile_height) in enumerate(tile_scan_boxes(image)):
            tile = image.crop((tile_x, tile_y, tile_x + tile_width, tile_y + tile_height))
            for face in detector.detect_faces(tile):
                faces.append(
                    {
                        **face,
                        "x": face["x"] + tile_x,
                        "y": face["y"] + tile_y,
                        "model_range": "full_range_tile",
                        "tile_index": tile_index,
                    }
                )
    finally:
        detector.min_detection_confidence = previous_confidence
    return faces


def tile_scan_boxes(image: Image.Image):
    tile_width = min(image.width, max(1, int(round(image.width * TILE_SCAN_TILE_RATIO))))
    tile_height = min(image.height, max(1, int(round(image.height * TILE_SCAN_TILE_RATIO))))
    x_positions = [0, image.width - tile_width]
    y_positions = [0, image.height - tile_height]
    boxes = []
    seen = set()
    for tile_y in y_positions:
        for tile_x in x_positions:
            box = (tile_x, tile_y, tile_width, tile_height)
            if box not in seen:
                boxes.append(box)
                seen.add(box)
    return boxes


def is_plausible_detected_face(face, image_width: int, image_height: int):
    width = face["width"]
    height = face["height"]
    if width <= 0 or height <= 0:
        return False

    aspect_ratio = width / height
    if not 0.45 <= aspect_ratio <= 2.2:
        return False

    min_side = min(image_width, image_height)
    max_dimension_ratio = max(width, height) / min_side
    confidence = face.get("score", 0.0)
    if confidence < 0.45 and max_dimension_ratio > 0.35:
        return False
    if confidence < 0.20 and max_dimension_ratio > 0.18:
        return False
    if confidence < 0.35 and max_dimension_ratio > 0.20:
        touches_image_edge = (
            face["x"] <= 1
            or face["y"] <= 1
            or face["x"] + width >= image_width - 1
            or face["y"] + height >= image_height - 1
        )
        if touches_image_edge:
            return False

    return True


def save_pending_detection(record):
    pending_path = DETECTIONS_DIR / f"{record['task_id']}.json"
    pending_path.write_text(json.dumps(record, indent=2), encoding="utf-8")


def read_pending_detection(task_id: str):
    pending_path = DETECTIONS_DIR / f"{task_id}.json"
    if not pending_path.exists():
        raise HTTPException(status_code=404, detail="Detection task not found. Run face detection again.")
    try:
        return json.loads(pending_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Detection task metadata is corrupted.") from exc


def save_task_history(record):
    if supabase_gateway.enabled:
        supabase_gateway.insert_task(record)
        return

    records = read_local_history(limit=5000)
    records.insert(0, record)
    LOCAL_HISTORY_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")


def read_local_history(limit):
    if not LOCAL_HISTORY_PATH.exists():
        return []
    try:
        records = json.loads(LOCAL_HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return records[:limit]


def filter_face_candidates(candidates):
    face_nms_iou_threshold = 0.35
    crop_nms_iou_threshold = 0.18

    candidates = sorted(
        candidates,
        key=lambda candidate: candidate["face_bbox"]["confidence"],
        reverse=True,
    )
    kept = []
    for candidate in candidates:
        if all(
            not candidate_overlaps_kept(
                candidate,
                kept_candidate,
                face_nms_iou_threshold,
                crop_nms_iou_threshold,
            )
            for kept_candidate in kept
        ):
            kept.append(candidate)

    return kept


def candidate_overlaps_kept(candidate, kept_candidate, face_iou_threshold, crop_iou_threshold):
    if bbox_iou(candidate["face_bbox"], kept_candidate["face_bbox"]) >= face_iou_threshold:
        return True

    return bbox_iou(candidate["crop_bbox"], kept_candidate["crop_bbox"]) >= crop_iou_threshold


def bbox_iou(box_a, box_b):
    ax1 = box_a["x_min"]
    ay1 = box_a["y_min"]
    ax2 = ax1 + box_a["width"]
    ay2 = ay1 + box_a["height"]
    bx1 = box_b["x_min"]
    by1 = box_b["y_min"]
    bx2 = bx1 + box_b["width"]
    by2 = by1 + box_b["height"]

    intersection_width = max(0, min(ax2, bx2) - max(ax1, bx1))
    intersection_height = max(0, min(ay2, by2) - max(ay1, by1))
    intersection = intersection_width * intersection_height
    if intersection == 0:
        return 0.0

    area_a = box_a["width"] * box_a["height"]
    area_b = box_b["width"] * box_b["height"]
    return intersection / (area_a + area_b - intersection)


def expand_face_bbox(
    x: int,
    y: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
    crop_scale: float,
    shoulder_bias: float,
):
    crop_size = int(round(max(width, height) * crop_scale))
    crop_size = max(1, min(crop_size, image_width, image_height))
    center_x = x + width / 2
    center_y = y + height / 2 + height * shoulder_bias * 0.35

    crop_x = int(round(center_x - crop_size / 2))
    crop_y = int(round(center_y - crop_size / 2))

    crop_x = max(0, min(crop_x, image_width - crop_size))
    crop_y = max(0, min(crop_y, image_height - crop_size))

    return {
        "x_min": crop_x,
        "y_min": crop_y,
        "width": crop_size,
        "height": crop_size,
        "image_width": image_width,
        "image_height": image_height,
    }

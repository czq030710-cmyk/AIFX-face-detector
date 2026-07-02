from base64 import b64encode
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from core_ai.face_detector import FaceDetector
from backend.supabase_client import SupabaseGateway, UserContext


app = FastAPI(title="AIFX Phase 1 Face Processing API")
detector = FaceDetector()
supabase_gateway = SupabaseGateway()

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
ORIGINALS_DIR = STORAGE_DIR / "originals"
CROPS_DIR = STORAGE_DIR / "crops"
LOCAL_HISTORY_PATH = STORAGE_DIR / "task_history.json"
for directory in (ORIGINALS_DIR, CROPS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")


class AuthCredentials(BaseModel):
    email: str
    password: str


def get_current_user(authorization: str | None = Header(default=None)) -> UserContext:
    return supabase_gateway.get_user_from_authorization(authorization)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "aifx-face-processing-api"}


@app.get("/config")
def get_config():
    return {
        "supabase_enabled": supabase_gateway.enabled,
        "storage_provider": "supabase" if supabase_gateway.enabled else "local",
    }


@app.post("/auth/signup")
def sign_up(credentials: AuthCredentials):
    return supabase_gateway.sign_up(credentials.email, credentials.password)


@app.post("/auth/login")
def sign_in(credentials: AuthCredentials):
    return supabase_gateway.sign_in(credentials.email, credentials.password)


@app.get("/tasks")
def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
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
    crop_scale: float = Form(2.2),
    shoulder_bias: float = Form(0.2),
    user: UserContext = Depends(get_current_user),
):
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Only .jpg and .png images are supported.")
    if not 0.0 <= min_detection_confidence <= 1.0:
        raise HTTPException(status_code=400, detail="min_detection_confidence must be between 0.0 and 1.0.")
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
    original_extension = ".jpg" if file.content_type == "image/jpeg" else ".png"
    original_filename = f"{task_id}_original{original_extension}"
    original_path = ORIGINALS_DIR / original_filename
    original_buffer = BytesIO()
    image.save(original_buffer, format="JPEG" if original_extension == ".jpg" else "PNG")
    original_bytes = original_buffer.getvalue()
    original_path.write_bytes(original_bytes)
    original_image_url = f"/storage/originals/{original_filename}"
    if supabase_gateway.enabled:
        original_image_url = supabase_gateway.upload_bytes(
            f"{user.user_id}/{task_id}/original{original_extension}",
            original_bytes,
            file.content_type,
        )

    detector.min_detection_confidence = min_detection_confidence
    faces = detector.detect_faces(image)
    cropped_faces = []
    cropped_image_urls = []
    bounding_boxes = []

    face_candidates = []
    for detected_index, face in enumerate(faces):
        x = face["x"]
        y = face["y"]
        width = face["width"]
        height = face["height"]
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
        crop_filename = f"{task_id}_face_{face_index}.png"
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
            "face_bbox": face_bbox,
            "crop_bbox": crop_bbox,
        }
        bounding_boxes.append(bounding_box)
        cropped_faces.append(
            {
                "face_index": face_index,
                "filename": crop_filename,
                "url": crop_url,
                "bbox": crop_bbox,
                "face_bbox": face_bbox,
                "crop_bbox": crop_bbox,
                "preview_base64": b64encode(crop_bytes).decode("ascii"),
            }
        )

    response_payload = {
        "task_id": task_id,
        "status": "completed",
        "filename": file.filename,
        "user_id": user.user_id,
        "storage_provider": "supabase" if supabase_gateway.enabled else "local",
        "original_image_url": original_image_url,
        "cropped_image_urls": cropped_image_urls,
        "bounding_boxes": bounding_boxes,
        "min_detection_confidence": min_detection_confidence,
        "crop_scale": crop_scale,
        "shoulder_bias": shoulder_bias,
        "image_width": image.width,
        "image_height": image.height,
        "face_count": len(cropped_faces),
        "faces": cropped_faces,
        "message": "No faces detected." if not cropped_faces else "Faces detected.",
    }
    task_record = {
        "task_id": task_id,
        "user_id": user.user_id,
        "filename": file.filename,
        "status": "completed",
        "original_image_url": original_image_url,
        "cropped_image_urls": cropped_image_urls,
        "bounding_boxes": bounding_boxes,
        "face_count": len(cropped_faces),
        "image_width": image.width,
        "image_height": image.height,
        "settings": {
            "min_detection_confidence": min_detection_confidence,
            "crop_scale": crop_scale,
            "shoulder_bias": shoulder_bias,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_task_history(task_record)
    return response_payload


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
    crop_nms_iou_threshold = 0.10
    low_confidence_floor = 0.30
    enough_confident_faces = 3

    candidates = sorted(
        candidates,
        key=lambda candidate: candidate["face_bbox"]["confidence"],
        reverse=True,
    )
    kept = []
    for candidate in candidates:
        crop_bbox = candidate["crop_bbox"]
        if all(bbox_iou(crop_bbox, kept_candidate["crop_bbox"]) < crop_nms_iou_threshold for kept_candidate in kept):
            kept.append(candidate)

    confident_count = sum(
        candidate["face_bbox"]["confidence"] >= low_confidence_floor
        for candidate in kept
    )
    if confident_count >= enough_confident_faces:
        kept = [
            candidate
            for candidate in kept
            if candidate["face_bbox"]["confidence"] >= low_confidence_floor
        ]

    return kept


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

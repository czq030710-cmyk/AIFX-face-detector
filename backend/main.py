from base64 import b64encode
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from core_ai.face_detector import FaceDetector


app = FastAPI(title="AIFX Phase 1 Face Processing API")
detector = FaceDetector()

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
ORIGINALS_DIR = STORAGE_DIR / "originals"
CROPS_DIR = STORAGE_DIR / "crops"
for directory in (ORIGINALS_DIR, CROPS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "aifx-face-processing-api"}


@app.post("/detect-faces")
async def detect_faces(
    file: UploadFile = File(...),
    min_detection_confidence: float = Form(0.5),
    crop_scale: float = Form(3.0),
    shoulder_bias: float = Form(0.8),
):
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Only .jpg and .png images are supported.")
    if not 0.0 <= min_detection_confidence <= 1.0:
        raise HTTPException(status_code=400, detail="min_detection_confidence must be between 0.0 and 1.0.")
    if not 1.0 <= crop_scale <= 5.0:
        raise HTTPException(status_code=400, detail="crop_scale must be between 1.0 and 5.0.")
    if not 0.0 <= shoulder_bias <= 1.5:
        raise HTTPException(status_code=400, detail="shoulder_bias must be between 0.0 and 1.5.")

    image_bytes = await file.read()
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.") from exc

    task_id = str(uuid4())
    original_extension = ".jpg" if file.content_type == "image/jpeg" else ".png"
    original_filename = f"{task_id}_original{original_extension}"
    original_path = ORIGINALS_DIR / original_filename
    image.save(original_path)
    original_image_url = f"/storage/originals/{original_filename}"

    detector.min_detection_confidence = min_detection_confidence
    faces = detector.detect_faces(image)
    cropped_faces = []
    cropped_image_urls = []
    bounding_boxes = []

    for face_index, face in enumerate(faces):
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
        cropped_image_urls.append(crop_url)
        face_bbox = {
            "face_index": face_index,
            "x_min": x,
            "y_min": y,
            "width": width,
            "height": height,
            "confidence": face["score"],
            "image_width": image.width,
            "image_height": image.height,
        }
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

    return {
        "task_id": task_id,
        "status": "completed",
        "filename": file.filename,
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
    crop_width = width * crop_scale
    crop_height = height * crop_scale * 1.25
    center_x = x + width / 2
    center_y = y + height / 2 + height * shoulder_bias

    crop_x = int(round(center_x - crop_width / 2))
    crop_y = int(round(center_y - crop_height / 2))
    crop_w = int(round(crop_width))
    crop_h = int(round(crop_height))

    crop_x = max(0, min(crop_x, image_width - 1))
    crop_y = max(0, min(crop_y, image_height - 1))
    crop_w = max(1, min(crop_w, image_width - crop_x))
    crop_h = max(1, min(crop_h, image_height - crop_y))

    return {
        "x_min": crop_x,
        "y_min": crop_y,
        "width": crop_w,
        "height": crop_h,
        "image_width": image_width,
        "image_height": image_height,
    }

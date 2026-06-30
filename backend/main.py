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
):
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Only .jpg and .png images are supported.")
    if not 0.0 <= min_detection_confidence <= 1.0:
        raise HTTPException(status_code=400, detail="min_detection_confidence must be between 0.0 and 1.0.")

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
        crop = image.crop((x, y, x + width, y + height))

        buffer = BytesIO()
        crop.save(buffer, format="PNG")
        crop_bytes = buffer.getvalue()
        crop_filename = f"{task_id}_face_{face_index}.png"
        crop_path = CROPS_DIR / crop_filename
        crop_path.write_bytes(crop_bytes)

        crop_url = f"/storage/crops/{crop_filename}"
        cropped_image_urls.append(crop_url)
        bbox = {
            "face_index": face_index,
            "x_min": x,
            "y_min": y,
            "width": width,
            "height": height,
            "confidence": face["score"],
            "image_width": image.width,
            "image_height": image.height,
        }
        bounding_boxes.append(bbox)
        cropped_faces.append(
            {
                "face_index": face_index,
                "filename": crop_filename,
                "url": crop_url,
                "bbox": bbox,
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
        "image_width": image.width,
        "image_height": image.height,
        "face_count": len(cropped_faces),
        "faces": cropped_faces,
        "message": "No faces detected." if not cropped_faces else "Faces detected.",
    }

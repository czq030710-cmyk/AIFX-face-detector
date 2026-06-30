# AIFX Face Detector

Phase 1 local prototype for AIFX Studio face detection, cropping, and task-history groundwork.

## Current Status

- Face detection core is implemented in `core_ai/face_detector.py`.
- The local detector uses official MediaPipe BlazeFace model files with OpenCV DNN inference for macOS stability.
- The default model is `core_ai/models/blaze_face_full_range.tflite`, which performs better on full-body images where faces are small.
- `core_ai/models/blaze_face_short_range.tflite` remains available as a fallback model.
- FastAPI provides `/health` and `/detect-faces`.
- Streamlit provides a local upload workspace.
- The Streamlit sidebar has a confidence-threshold slider and manual input for tuning detection sensitivity.
- Day 2 local storage flow is in place: uploaded originals and cropped faces are saved under `storage/` and returned as local URLs.
- Supabase Auth, Storage, task history, Docker, and full README setup are next.

## Working Agreement

After each completed implementation step:

1. Update this README with the new project status or usage notes.
2. Run the relevant smoke tests.
3. Commit and push the updated code to GitHub.

## Local Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run Backend

```bash
uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
```

## Run Frontend

In another terminal:

```bash
source venv/bin/activate
streamlit run frontend/app.py
```

The frontend expects the API at:

```text
http://127.0.0.1:8000
```

Override with:

```bash
API_URL=http://127.0.0.1:8000 streamlit run frontend/app.py
```

## Detection Tuning

The frontend exposes two controls for the same backend parameter:

- `Confidence threshold` slider
- `Manual threshold` numeric input

The value is sent to `POST /detect-faces` as:

```text
min_detection_confidence
```

Suggested values:

- `0.50`: default, cleaner results for most images.
- `0.35`: better recall for smaller faces.
- `0.25`: useful for difficult images, but may introduce false positives.

Lower values find more faces; higher values filter more aggressively.

## API Response Shape

`POST /detect-faces` returns:

- `task_id`
- `original_image_url`
- `cropped_image_urls`
- `bounding_boxes`
- `min_detection_confidence`
- `face_count`
- `faces`

Bounding boxes are stored in original image pixel coordinates:

```json
{
  "face_index": 0,
  "x_min": 185,
  "y_min": 214,
  "width": 174,
  "height": 174,
  "confidence": 0.8444,
  "image_width": 512,
  "image_height": 512
}
```

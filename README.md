# AIFX Face Detector

Phase 1 local prototype for AIFX Studio face detection, cropping, and task-history groundwork.

## Current Status

- Face detection core is implemented in `core_ai/face_detector.py`.
- The local detector uses official MediaPipe BlazeFace model files with OpenCV DNN inference for macOS stability.
- The default model is `core_ai/models/blaze_face_full_range.tflite`, which performs better on full-body images where faces are small.
- `core_ai/models/blaze_face_short_range.tflite` remains available as a fallback model.
- FastAPI provides `/health` and `/detect-faces`.
- Streamlit provides a local upload workspace.
- The Streamlit sidebar has linked slider-plus-number controls for confidence, crop expansion, and vertical crop offset.
- Detection results are drawn back onto the full original image so crop locations can be visually checked.
- Green boxes show the saved crop region on the original image.
- Day 2 local storage flow is in place: uploaded originals and cropped faces are saved under `storage/` and returned as local URLs.
- Cropped face files are saved for later backend/Supabase use, but the frontend keeps them hidden and shows only metadata plus saved URLs.
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

## Detection And Crop Tuning

The frontend exposes controls for the main detection and crop parameters:

- `Confidence threshold`
- `Crop expansion`
- `Vertical offset`

Each control pairs a slider with a precise number input. Changing either side updates the same value, so manual edits and slider movement stay in sync.
Hover over a control label in the frontend to see a short explanation of what that parameter changes.

Default recommended preset:

- `Confidence threshold`: `0.23`
- `Crop expansion`: `2.20`
- `Vertical offset`: `0.20`

The values are sent to `POST /detect-faces` as:

```text
min_detection_confidence
crop_scale
shoulder_bias
```

The tuning controls use `0.01` increments. Suggested confidence values:

- `0.5`: default, cleaner results for most images.
- `0.3`: better recall for smaller faces.
- `0.2`: useful for difficult images, but may introduce false positives.

Lower values find more faces; higher values filter more aggressively.

Crop controls:

- `crop_scale`: expands the detected face box into a larger square portrait-style crop.
- `shoulder_bias`: shifts the square crop vertically without changing its square shape.

Parameter meanings:

- `min_detection_confidence`: how strict face detection is. Lower values improve recall; higher values reduce false positives.
- `crop_scale`: how large the final square crop is around the detected face.
- `shoulder_bias`: vertical crop offset. Negative values move the crop upward, `0` keeps it centered, and positive values move it downward to include more shoulders.

The backend also applies a second filtering pass after the model returns candidate faces:

- Overlapping final crop boxes are suppressed so repeated detections around the same person collapse to the best-scoring box.
- If at least three confident faces are found, very low-confidence leftovers are dropped to reduce decorative false positives from face-like textures.

The API stores the expanded crop image under `storage/crops/`, while the response keeps both coordinate sets:

- `face_bbox`: the smaller model-detected face region.
- `crop_bbox`: the expanded region actually saved as the cropped image.

## API Response Shape

`POST /detect-faces` returns:

- `task_id`
- `original_image_url`
- `cropped_image_urls`
- `bounding_boxes`
- `min_detection_confidence`
- `crop_scale`
- `shoulder_bias`
- `face_count`
- `faces`

Bounding boxes are stored in original image pixel coordinates. Each face includes both the detected face box and the expanded crop box:

```json
{
  "face_index": 0,
  "face_bbox": {
    "x_min": 185,
    "y_min": 214,
    "width": 174,
    "height": 174,
    "confidence": 0.8444,
    "image_width": 512,
    "image_height": 512
  },
  "crop_bbox": {
    "x_min": 0,
    "y_min": 0,
    "width": 512,
    "height": 512,
    "image_width": 512,
    "image_height": 512
  }
}
```

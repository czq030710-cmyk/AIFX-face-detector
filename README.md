# AIFX Face Detector

Phase 1 local prototype for AIFX Studio face detection, cropping, and task-history groundwork.

## Current Status

- Face detection core is implemented in `core_ai/face_detector.py`.
- The local detector uses official MediaPipe BlazeFace model files with OpenCV DNN inference for macOS stability.
- The detection API supports `short_range`, `full_range`, and `balanced`, while the frontend automatically uses the best recall-first `balanced` strategy.
- `balanced` mode runs both MediaPipe ranges on the original image, removes duplicate face or crop regions, and sorts candidates by confidence so the user can manually choose the true faces before cropping.
- FastAPI provides `/health`, `/detect-faces`, and `/crop-selected`.
- Streamlit provides a compact Apple-inspired workspace with a polished plus-button upload entry, detect-first flow, and select-then-crop output.
- The workspace keeps detected face rows inside a fixed-height scroll panel.
- The Streamlit sidebar has separate linked slider-plus-number controls for distant-face and close-face sensitivity.
- The frontend no longer uses tile-based small-face scanning by default; detection stays on the original image for simpler tuning and lower compute cost.
- The login-first page has an Apple-like animated product layout with glass styling and a reduced-motion fallback.
- Crop expansion and vertical offset are hidden inside the `Crop box tuning` expander until portrait framing needs adjustment.
- Detection results are drawn back onto the full original image so crop locations can be visually checked before saving crops.
- Green boxes show the proposed crop regions on the original image.
- The right-side detected-face list scrolls internally when many faces are found, so the main workspace stays short.
- Day 2 local storage flow is in place: uploaded originals and cropped faces are saved under `storage/` and returned as local URLs.
- Cropped face files are saved only after the user selects one or more detected faces and starts the crop step.
- Day 3 auth/storage/history flow is implemented.
- If Supabase credentials are configured, the app uses Supabase Auth, Storage, and the `task_history` table with per-user history.
- If Supabase credentials are configured, users must log in before using the workspace.
- If Supabase credentials are missing, the app stays usable in local demo mode and writes task history to `storage/task_history.json`.
- The task history view shows the latest 10 tasks for the current logged-in user.
- Saved original and crop filenames keep the uploaded image name plus a short task id, for example `abc-original-a1b2c3d4.png` and `abc-crops-01-a1b2c3d4.png`.
- Docker and final QA are next.

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

Optional environment setup:

```bash
cp .env.example .env
```

Leave Supabase values empty for local demo mode. Fill them to enable Day 3 cloud auth, storage, and user-isolated history.

## Run Backend

```bash
uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
```

Also available:

```text
http://127.0.0.1:8000/config
http://127.0.0.1:8000/tasks
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

## Supabase Setup

Day 3 is wired for Supabase but still works without credentials.

1. Create a Supabase project.
2. Open the Supabase SQL editor.
3. Run `database/schema.sql`.
4. Copy `.env.example` to `.env`.
5. Fill:

```text
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_BUCKET=face-processing
```

When all three Supabase keys are set, the backend enables cloud accounts:

- `/auth/signup` creates users through Supabase Auth.
- `/auth/login` returns a Bearer token used by the frontend.
- `/detect-faces` requires login, uploads the original image, detects candidate faces, and returns selectable crop previews.
- `/crop-selected` requires login, saves only the selected crop images, and writes a `task_history` row.
- `/tasks` requires login and returns the latest 10 tasks for that user's Supabase history.

When Supabase is configured, the frontend shows a login-first page. After login, the same browser session stays signed in while the app is running.

Local demo mode:

- No login is required.
- Uploaded originals and crops are saved under `storage/`.
- Task history is saved to `storage/task_history.json`.

## Detection And Crop Tuning

The frontend exposes controls for the main detection and crop parameters:

- `Distant-face sensitivity`
- `Close-face sensitivity`
- `Crop expansion` under `Crop box tuning`
- `Vertical offset` under `Crop box tuning`

Each control pairs a slider with a precise number input. Changing either side updates the same value, so manual edits and slider movement stay in sync.
Hover over a control label in the frontend to see a short explanation of what that parameter changes.

Default recommended preset:

- Detection strategy: `Balanced recall`, applied automatically.
- `Distant-face sensitivity`: `0.15`
- `Close-face sensitivity`: `0.23`
- `Crop expansion`: `2.20`
- `Vertical offset`: `0.20`

The values are sent to `POST /detect-faces` as:

```text
min_detection_confidence
detection_range
full_range_confidence
short_range_confidence
crop_scale
shoulder_bias
```

The frontend no longer asks the user to choose a model. It always sends the backend's `Balanced recall` strategy: one full-range MediaPipe BlazeFace pass plus one short-range MediaPipe BlazeFace pass on the original image. The backend then merges duplicate detections and keeps the candidate list sorted by confidence.

Tile-based small-face scanning is not part of the default workflow. It was removed from the automatic path because it costs more compute, can split faces near tile boundaries, and adds extra tuning complexity. Very low-resolution distant photos where each face is only a few pixels wide can still hit the BlazeFace model limit, so they are not used as the default tuning target.

How to tune the two model thresholds:

- Lower `Distant-face sensitivity` first when small or distant faces are missing.
- Lower `Close-face sensitivity` when close faces are still missing.
- Raise `Close-face sensitivity` if large nearby faces create too many obvious false positives.
- For extremely low-resolution distant images, try a higher-resolution source image instead of pushing the default thresholds too low.

The confidence controls use `0.01` increments. Suggested values:

- `0.5`: default, cleaner results for most images.
- `0.3`: better recall for smaller faces.
- `0.1` to `0.2`: useful for difficult images, but may introduce false positives.

Lower values find more faces; higher values filter more aggressively.

Crop controls:

- `crop_scale`: expands the detected face box into a larger square portrait-style crop.
- `shoulder_bias`: shifts the square crop vertically without changing its square shape.

Parameter meanings:

- `detection_range`: set by the frontend to `balanced`.
- `full_range_confidence`: exposed as `Distant-face sensitivity`.
- `short_range_confidence`: exposed as `Close-face sensitivity`.
- `min_detection_confidence`: legacy fallback used only if the model-specific confidence values are not provided.
- `crop_scale`: how large the final square crop is around the detected face.
- `shoulder_bias`: vertical crop offset. Negative values move the crop upward, `0` keeps it centered, and positive values move it downward to include more shoulders.

The backend also applies a second filtering pass after the model returns candidate faces:

- Duplicate model detections are suppressed using the smaller detected face boxes, not the expanded crop boxes.
- Remaining candidates are sorted from highest to lowest confidence before being numbered in the UI.
- Low-confidence candidates are kept so difficult or distant faces can still be reviewed manually.

The API now runs in two stages:

1. `POST /detect-faces` stores the original image, detects all candidate faces, and returns preview crops plus coordinates. It does not save crop files or write final history.
2. `POST /crop-selected` receives a `task_id` and selected `face_index` values, then saves only those crop files and writes the final task history row.

The API stores selected expanded crop images under `storage/crops/`, while the response keeps both coordinate sets:

- `face_bbox`: the smaller model-detected face region.
- `crop_bbox`: the expanded region actually saved as the cropped image.

Saved file naming:

- Uploaded `abc.png` is stored locally as `storage/originals/abc-original-<task8>.png`.
- Selected crops from that image are stored locally as `storage/crops/abc-crops-01-<task8>.png`, `abc-crops-02-<task8>.png`, and so on.
- Supabase Storage uses the same filenames under `{user_id}/{task_id}/originals/` and `{user_id}/{task_id}/crops/`.
- The short task id suffix prevents repeated uploads with the same original filename from overwriting each other.

## API Response Shape

`POST /detect-faces` returns:

- `task_id`
- `original_image_url`
- `cropped_image_urls` as an empty list during detection
- `bounding_boxes`
- `user_id`
- `storage_provider`
- `min_detection_confidence`
- `detection_range`
- `full_range_confidence`
- `short_range_confidence`
- `crop_scale`
- `shoulder_bias`
- `face_count`
- `faces`

`POST /crop-selected` accepts:

```json
{
  "task_id": "detection-task-id",
  "selected_face_indices": [0, 2]
}
```

It returns the saved crop URLs and writes the completed task to history.

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

## Day 3 Completion Notes

Implemented:

- Supabase Auth endpoints: `POST /auth/signup`, `POST /auth/login`.
- Auth-aware detection: Supabase mode uses Bearer token user identity; local demo mode uses a local user id.
- Supabase Storage upload path: `{user_id}/{task_id}/originals/{source}-original-{task8}.*` after detection and `{user_id}/{task_id}/crops/{source}-crops-01-{task8}.png` after selected crop output.
- Task history persistence: Supabase `task_history` table or local `storage/task_history.json`.
- Login-first frontend session controls and latest-10 history tab.
- Database/storage schema in `database/schema.sql`.

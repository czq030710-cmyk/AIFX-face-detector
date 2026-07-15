# Phase 2 Deployment Notes

## Recommended topology

- Cloud API: FastAPI container on Google Cloud Run.
- Cloud data: Supabase Postgres and the four Supabase Storage buckets.
- Private worker: `python -m backend.worker` on a Mac/Linux host that can reach the Windows ComfyUI LAN address.
- Private inference: ComfyUI stays on Windows and is never exposed directly to public clients.
- Frontend: Streamlit can remain local during validation or be deployed separately after the API URL is stable.

The worker, not Cloud Run, calls ComfyUI. A Cloud Run service cannot reach a private `192.168.x.x` host unless a VPN or private network tunnel is configured.

## Files that must remain private

- `.env`
- `config/lora_config.json`
- `config/comfyui_config.json`
- `backend/workflows/zooey.json`

The Docker build intentionally excludes these files. Mount `config/lora_config.json` from Google Secret Manager into the Cloud Run API because authenticated users need the private character catalog and the API validates character ids when creating jobs. Provide all three JSON files to the private worker locally. Mount the node mapping and workflow in Cloud Run only if the synchronous `/api/v1/face-enhance` diagnostic endpoint must run there.

## Cloud Run API build

Set your own project and region first:

```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud builds submit --tag REGION-docker.pkg.dev/YOUR_GCP_PROJECT_ID/aifx/aifx-api:phase2
```

Deploy the API with Supabase values stored in Secret Manager. Do not place service-role or worker keys directly in shell history:

```bash
gcloud run deploy aifx-api \
  --image REGION-docker.pkg.dev/YOUR_GCP_PROJECT_ID/aifx/aifx-api:phase2 \
  --region REGION \
  --port 8080 \
  --no-allow-unauthenticated
```

Then configure these runtime values through the Cloud Run console or Secret Manager:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_ORIGINAL_BUCKET
SUPABASE_CROP_BUCKET
SUPABASE_ENHANCED_CROP_BUCKET
SUPABASE_ENHANCED_ORIGINAL_BUCKET
AIFX_PHASE2_API_KEYS (optional when using Supabase Auth)
AIFX_WORKER_API_KEY (only for the optional manual worker endpoint)
```

## Private worker startup

On the Mac/Linux machine that can reach ComfyUI:

```bash
cd /path/to/aifx-phase1
source venv/bin/activate
set -a
source .env
set +a
python -m backend.worker
```

The private worker needs Supabase credentials, `COMFYUI_URL`, the private workflow, the private node mapping, and the private character catalog. It does not need a public inbound port.

## Production checks

1. `GET /health` returns HTTP 200.
2. The frontend can create an `enhancement_jobs` row.
3. The private worker changes one face from `queued` to `comfyui_processing` and then `completed`.
4. Enhanced crops appear in `aifx-enhanced-crops`.
5. The final blended image appears in `aifx-enhanced-originals`.
6. Failed jobs stop at `max_retries` and can be retried manually.
7. No private JSON file, LoRA filename, service-role key, LAN address, or ComfyUI UI is public.

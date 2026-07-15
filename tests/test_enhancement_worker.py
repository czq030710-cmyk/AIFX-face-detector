from copy import deepcopy
from io import BytesIO
import unittest
from unittest.mock import patch

from PIL import Image

import backend.main as main
from backend.comfyui_client import ComfyUIImage
from backend.image_blender import encode_png


class FakeGateway:
    def __init__(self):
        self.job = {
            "job_id": "20260715_01",
            "user_id": "test-user",
            "status": "queued",
            "original_url": "https://cloud/original.png",
            "feather_radius": 6,
        }
        self.face = {
            "id": "face-row-1",
            "job_id": self.job["job_id"],
            "user_id": self.job["user_id"],
            "face_id": "face_001",
            "status": "queued",
            "character_id": "character-a",
            "prompt": "",
            "crop_url": "https://cloud/crop.png",
            "crop_bbox": {"x_min": 20, "y_min": 20, "width": 40, "height": 40},
            "retry_count": 0,
            "max_retries": 3,
        }
        self.objects = {}
        self.claimed = False

    def claim_next_enhancement_face(self):
        if self.claimed:
            return None
        self.claimed = True
        self.face["status"] = "processing"
        return deepcopy(self.face)

    def update_enhancement_job(self, job_id, user, fields):
        self.job.update(fields)
        return deepcopy(self.job)

    def get_enhancement_job(self, job_id, user):
        return deepcopy(self.job)

    def list_enhancement_faces(self, job_id, user_id):
        return [deepcopy(self.face)]

    def update_enhancement_face(self, face_id, fields):
        self.face.update(fields)
        return deepcopy(self.face)

    def mark_enhancement_face_failure(self, face, error_message):
        raise AssertionError(f"Worker unexpectedly failed: {error_message}")

    def bucket_for_asset(self, asset_type):
        return f"bucket-{asset_type}"

    def upload_bytes(self, path, data, content_type, bucket_name=None, upsert=False):
        url = f"https://cloud/{bucket_name}/{path}"
        self.objects[url] = data
        return url


class FakeComfyUIClient:
    def __init__(self, base_url, timeout_seconds):
        self.base_url = base_url

    def upload_image(self, image_bytes, filename):
        return filename

    def submit_prompt(self, workflow):
        return "prompt-test"

    def wait_for_output(self, prompt_id, output_node_id):
        return ComfyUIImage("enhanced.png", "phase2", "output")

    def fetch_image(self, image):
        return encode_png(Image.new("RGB", (40, 40), (240, 40, 40)))


class EnhancementWorkerTests(unittest.TestCase):
    def test_worker_completes_face_and_blends_final_image(self):
        gateway = FakeGateway()
        original = encode_png(Image.new("RGB", (80, 80), (20, 40, 180)))
        crop = encode_png(Image.new("RGB", (40, 40), (20, 40, 180)))

        def fake_download(url):
            if url == gateway.job["original_url"]:
                return original
            if url == gateway.face["crop_url"]:
                return crop
            return gateway.objects[url]

        with (
            patch.object(main, "supabase_gateway", gateway),
            patch.object(main, "ComfyUIClient", FakeComfyUIClient),
            patch.object(main, "download_cloud_image_bytes", fake_download),
            patch.object(
                main,
                "resolve_character_lora",
                lambda character_id: {"character_id": character_id, "lora_name": "private-test.safetensors"},
            ),
            patch.object(main, "build_comfyui_workflow", lambda **kwargs: {"test": kwargs["job_id"]}),
        ):
            result = main.process_next_enhancement_face()

        self.assertEqual(result["face_status"], "completed")
        self.assertEqual(result["job_status"], "completed")
        self.assertTrue(gateway.face["enhanced_crop_url"].startswith("https://cloud/"))
        self.assertTrue(gateway.job["enhanced_original_url"].startswith("https://cloud/"))
        final_image = Image.open(BytesIO(gateway.objects[gateway.job["enhanced_original_url"]]))
        self.assertEqual(final_image.size, (80, 80))


if __name__ == "__main__":
    unittest.main()

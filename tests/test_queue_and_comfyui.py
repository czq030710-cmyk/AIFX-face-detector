import unittest

from backend.comfyui_client import ComfyUIClient
from backend.supabase_client import SupabaseGateway, UserContext


class QueueAndComfyUITests(unittest.TestCase):
    def test_extracts_requested_comfyui_output_node(self):
        history = {
            "prompt-1": {
                "outputs": {
                    "output-node": {
                        "images": [
                            {
                                "filename": "result.png",
                                "subfolder": "phase2",
                                "type": "output",
                            }
                        ]
                    }
                }
            }
        }
        image = ComfyUIClient._extract_output_image(history, "prompt-1", "output-node")
        self.assertIsNotNone(image)
        self.assertEqual(image.filename, "result.png")
        self.assertEqual(image.subfolder, "phase2")

    def test_retry_stops_at_configured_limit(self):
        gateway = SupabaseGateway.__new__(SupabaseGateway)
        captured = {}

        def fake_update(face_id, fields):
            captured.update(fields)
            return {"id": face_id, **fields}

        gateway.update_enhancement_face = fake_update
        result = gateway.mark_enhancement_face_failure(
            face={"id": "face-row", "retry_count": 2, "max_retries": 3},
            error_message="test failure",
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["retry_count"], 3)
        self.assertIsNone(result["next_retry_at"])
        self.assertEqual(captured["last_error"], "test failure")

    def test_user_context_is_not_required_for_worker_retry_math(self):
        user = UserContext("user-1", None, None, True)
        self.assertEqual(user.user_id, "user-1")


if __name__ == "__main__":
    unittest.main()

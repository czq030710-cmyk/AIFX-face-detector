from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import time
from typing import Any
from uuid import uuid4

import requests


@dataclass
class ComfyUIImage:
    filename: str
    subfolder: str
    image_type: str


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient:
    def __init__(self, base_url: str, timeout_seconds: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client_id = str(uuid4())

    def upload_image(self, image_bytes: bytes, filename: str) -> str:
        files = {
            "image": (filename, BytesIO(image_bytes), "image/png"),
        }
        data = {
            "type": "input",
            "overwrite": "true",
        }
        try:
            response = requests.post(
                f"{self.base_url}/upload/image",
                files=files,
                data=data,
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ComfyUIError(f"ComfyUI image upload failed: {exc}") from exc

        payload = response.json()
        image_name = payload.get("name")
        if not image_name:
            raise ComfyUIError("ComfyUI upload response did not include an image name.")
        return image_name

    def submit_prompt(self, workflow: dict[str, Any]) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ComfyUIError(f"ComfyUI prompt submission failed: {exc}") from exc

        payload = response.json()
        prompt_id = payload.get("prompt_id")
        if not prompt_id:
            raise ComfyUIError("ComfyUI prompt response did not include prompt_id.")
        return prompt_id

    def wait_for_output(self, prompt_id: str, output_node_id: str) -> ComfyUIImage:
        deadline = time.monotonic() + self.timeout_seconds
        last_history: dict[str, Any] | None = None

        while time.monotonic() < deadline:
            history = self._get_history(prompt_id)
            if history:
                last_history = history
                image = self._extract_output_image(history, prompt_id, output_node_id)
                if image:
                    return image
            time.sleep(1.5)

        raise ComfyUIError(
            f"Timed out waiting for ComfyUI output from node {output_node_id}. "
            f"Last history keys: {list(last_history or {})}"
        )

    def fetch_image(self, image: ComfyUIImage) -> bytes:
        params = {
            "filename": image.filename,
            "subfolder": image.subfolder,
            "type": image.image_type,
        }
        try:
            response = requests.get(
                f"{self.base_url}/view",
                params=params,
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ComfyUIError(f"ComfyUI output download failed: {exc}") from exc
        return response.content

    def _get_history(self, prompt_id: str) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{self.base_url}/history/{prompt_id}",
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ComfyUIError(f"ComfyUI history polling failed: {exc}") from exc
        return response.json()

    @staticmethod
    def _extract_output_image(
        history: dict[str, Any],
        prompt_id: str,
        output_node_id: str,
    ) -> ComfyUIImage | None:
        prompt_history = history.get(prompt_id, history)
        outputs = prompt_history.get("outputs", {})
        node_output = outputs.get(output_node_id, {})
        images = node_output.get("images", [])
        if not images:
            return None
        first_image = images[0]
        return ComfyUIImage(
            filename=first_image["filename"],
            subfolder=first_image.get("subfolder", ""),
            image_type=first_image.get("type", "output"),
        )

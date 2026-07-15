from __future__ import annotations

from io import BytesIO
from typing import Iterable

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError


class ImageBlendError(ValueError):
    pass


def load_rgb_image(image_bytes: bytes) -> Image.Image:
    try:
        return ImageOps.exif_transpose(Image.open(BytesIO(image_bytes))).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageBlendError("Image data is not a supported image.") from exc


def encode_png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def normalize_crop_bbox(bbox: dict, image_width: int, image_height: int) -> tuple[int, int, int, int]:
    try:
        x = int(bbox.get("x_min", bbox.get("xmin")))
        y = int(bbox.get("y_min", bbox.get("ymin")))
        width = int(bbox["width"])
        height = int(bbox["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ImageBlendError("crop_bbox must include x_min/y_min/width/height.") from exc

    if width <= 0 or height <= 0:
        raise ImageBlendError("crop_bbox width and height must be positive.")

    left = max(0, x)
    top = max(0, y)
    right = min(image_width, x + width)
    bottom = min(image_height, y + height)
    if right <= left or bottom <= top:
        raise ImageBlendError("crop_bbox falls outside the original image.")
    return left, top, right, bottom


def feather_mask(width: int, height: int, radius: int) -> Image.Image:
    if width <= 0 or height <= 0:
        raise ImageBlendError("Mask dimensions must be positive.")

    resolved_radius = max(0, min(int(radius), max(0, min(width, height) // 2 - 1)))
    if resolved_radius == 0:
        return Image.new("L", (width, height), 255)

    mask = Image.new("L", (width, height), 0)
    inner = Image.new(
        "L",
        (max(1, width - resolved_radius * 2), max(1, height - resolved_radius * 2)),
        255,
    )
    mask.paste(inner, (resolved_radius, resolved_radius))
    return mask.filter(ImageFilter.GaussianBlur(radius=max(0.5, resolved_radius / 3)))


def blend_enhanced_faces(
    original_bytes: bytes,
    enhanced_faces: Iterable[tuple[bytes, dict]],
    feather_radius: int = 24,
) -> bytes:
    original = load_rgb_image(original_bytes)
    canvas = original.copy()

    face_count = 0
    for enhanced_bytes, crop_bbox in enhanced_faces:
        left, top, right, bottom = normalize_crop_bbox(
            crop_bbox,
            canvas.width,
            canvas.height,
        )
        target_size = (right - left, bottom - top)
        enhanced = load_rgb_image(enhanced_bytes).resize(target_size, Image.Resampling.LANCZOS)
        mask = feather_mask(*target_size, feather_radius)
        region = canvas.crop((left, top, right, bottom))
        canvas.paste(Image.composite(enhanced, region, mask), (left, top))
        face_count += 1

    if face_count == 0:
        raise ImageBlendError("At least one enhanced face is required for blending.")
    return encode_png(canvas)

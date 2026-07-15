from io import BytesIO
import unittest

from PIL import Image

from backend.image_blender import (
    ImageBlendError,
    blend_enhanced_faces,
    encode_png,
    normalize_crop_bbox,
)


class ImageBlenderTests(unittest.TestCase):
    def test_blend_preserves_outside_and_replaces_center(self):
        original = Image.new("RGB", (100, 100), (0, 0, 255))
        enhanced = Image.new("RGB", (40, 40), (255, 0, 0))

        result_bytes = blend_enhanced_faces(
            encode_png(original),
            [(encode_png(enhanced), {"x_min": 30, "y_min": 30, "width": 40, "height": 40})],
            feather_radius=8,
        )
        result = Image.open(BytesIO(result_bytes)).convert("RGB")

        self.assertEqual(result.getpixel((10, 10)), (0, 0, 255))
        self.assertGreater(result.getpixel((50, 50))[0], 240)
        edge_pixel = result.getpixel((34, 50))
        self.assertGreater(edge_pixel[0], 0)
        self.assertGreater(edge_pixel[2], 0)

    def test_bbox_accepts_xmin_alias_and_clamps_to_image(self):
        self.assertEqual(
            normalize_crop_bbox(
                {"xmin": -5, "ymin": 10, "width": 20, "height": 30},
                100,
                100,
            ),
            (0, 10, 15, 40),
        )

    def test_bbox_outside_image_is_rejected(self):
        with self.assertRaises(ImageBlendError):
            normalize_crop_bbox(
                {"x_min": 120, "y_min": 10, "width": 20, "height": 20},
                100,
                100,
            )


if __name__ == "__main__":
    unittest.main()

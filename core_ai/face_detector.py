from pathlib import Path

import cv2
import numpy as np
from PIL import Image


class FaceDetector:
    def __init__(
        self,
        min_detection_confidence=0.5,
        model_path=None,
        model_range="full_range",
        input_size=None,
    ):
        """初始化人脸检测器，使用 MediaPipe 官方 BlazeFace 模型。"""
        self.min_detection_confidence = min_detection_confidence
        models_dir = Path(__file__).with_name("models")
        if model_path is None:
            default_model_path = models_dir / f"blaze_face_{model_range}.tflite"
            if not default_model_path.exists():
                default_model_path = models_dir / "blaze_face_full_range.tflite"
            if not default_model_path.exists():
                default_model_path = models_dir / "blaze_face_short_range.tflite"
        else:
            default_model_path = model_path
        self.model_path = Path(model_path or default_model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Face detector model not found: {self.model_path}")

        self.input_size = input_size or self._infer_input_size(self.model_path)
        self.net = cv2.dnn.readNetFromTFLite(str(self.model_path))
        self.output_names = self.net.getUnconnectedOutLayersNames()
        self.score_output_name, self.box_output_name = self._resolve_output_names()
        self.anchors = self._generate_anchors()

    def detect_faces(self, image: Image.Image):
        """输入 PIL 图片，返回检测到的人脸绝对像素坐标"""
        img_array = np.array(image.convert("RGB"))
        ih, iw = img_array.shape[:2]

        blob = cv2.dnn.blobFromImage(
            img_array,
            scalefactor=1.0 / 127.5,
            size=(self.input_size, self.input_size),
            mean=(127.5, 127.5, 127.5),
            swapRB=False,
            crop=False,
        )
        self.net.setInput(blob)
        outputs = dict(zip(self.output_names, self.net.forward(self.output_names)))

        raw_scores = outputs[self.score_output_name][0, :, 0]
        raw_boxes = outputs[self.box_output_name][0]

        boxes = []
        scores = []
        for anchor, raw_box, raw_score in zip(self.anchors, raw_boxes, raw_scores):
            score = self._sigmoid(raw_score)
            if score < self.min_detection_confidence:
                continue

            x_center = raw_box[0] / self.input_size + anchor[0]
            y_center = raw_box[1] / self.input_size + anchor[1]
            width = raw_box[2] / self.input_size
            height = raw_box[3] / self.input_size

            x = int((x_center - width / 2) * iw)
            y = int((y_center - height / 2) * ih)
            w = int(width * iw)
            h = int(height * ih)

            x = max(0, min(x, iw - 1))
            y = max(0, min(y, ih - 1))
            w = max(0, min(w, iw - x))
            h = max(0, min(h, ih - y))

            if w > 0 and h > 0:
                boxes.append([x, y, w, h])
                scores.append(float(score))

        keep = cv2.dnn.NMSBoxes(
            boxes,
            scores,
            score_threshold=self.min_detection_confidence,
            nms_threshold=0.3,
        )

        faces = []
        for index in np.array(keep).flatten():
            x, y, w, h = boxes[index]
            faces.append({"x": x, "y": y, "width": w, "height": h, "score": scores[index]})

        return faces

    def _generate_anchors(self):
        if self.input_size == 192:
            return self._generate_full_range_anchors()

        anchors = []
        for stride, anchors_per_cell in ((8, 2), (16, 6)):
            feature_map_size = self.input_size // stride
            for y in range(feature_map_size):
                for x in range(feature_map_size):
                    x_center = (x + 0.5) / feature_map_size
                    y_center = (y + 0.5) / feature_map_size
                    for _ in range(anchors_per_cell):
                        anchors.append((x_center, y_center))
        return np.array(anchors, dtype=np.float32)

    def _generate_full_range_anchors(self):
        anchors = []
        feature_map_size = self.input_size // 4
        for y in range(feature_map_size):
            for x in range(feature_map_size):
                x_center = (x + 0.5) / feature_map_size
                y_center = (y + 0.5) / feature_map_size
                anchors.append((x_center, y_center))
        return np.array(anchors, dtype=np.float32)

    def _resolve_output_names(self):
        output_names = set(self.output_names)
        if {"classificators", "regressors"}.issubset(output_names):
            return "classificators", "regressors"
        if {"reshaped_classifier_face_4", "reshaped_regressor_face_4"}.issubset(output_names):
            return "reshaped_classifier_face_4", "reshaped_regressor_face_4"
        raise RuntimeError(f"Unsupported face detector output layers: {self.output_names}")

    @staticmethod
    def _infer_input_size(model_path: Path):
        if "full_range" in model_path.name:
            return 192
        return 128

    @staticmethod
    def _sigmoid(value):
        value = np.clip(value, -100, 100)
        return 1.0 / (1.0 + np.exp(-value))

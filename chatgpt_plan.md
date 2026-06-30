# AI Face Detector 项目计划书

你是我的 Python + AI 项目导师。请按照下面计划，一步一步带我完成这个项目；每一步只教我做当前步骤，等我确认完成后再继续下一步。我的项目目录是 `aifx-phase1`，目标是做一个可以检测图片中人脸位置的基础 AI 功能模块。

## 当前背景

我原来的代码使用：

```python
import mediapipe as mp
mp.solutions.face_detection
```

但我安装的是新版 `mediapipe 0.10.35`，它的 Python 顶层模块不再提供 `mp.solutions`，所以运行时报错：

```text
AttributeError: module 'mediapipe' has no attribute 'solutions'
```

我不想通过降级 MediaPipe 解决，希望保持新版 MediaPipe。

另外，直接使用新版 `mediapipe.tasks.vision.FaceDetector` 在我的 macOS 环境中会触发底层 Metal/OpenGL 图形服务错误，进程可能直接崩溃。因此当前采用的实用方案是：

1. 保持最新版 `mediapipe`。
2. 使用 MediaPipe 官方 BlazeFace `.tflite` 人脸检测模型。
3. 用 `opencv-contrib-python` 的 `cv2.dnn.readNetFromTFLite()` 运行模型。
4. 保持 `FaceDetector.detect_faces(image)` 的输出格式不变，返回人脸框坐标列表。

## 项目结构

目标结构：

```text
aifx-phase1/
  core_ai/
    face_detector.py
    test_ai.py
    models/
      blaze_face_short_range.tflite
  requirements.txt
```

## 依赖

`requirements.txt` 至少包含：

```text
fastapi
uvicorn
mediapipe
Pillow
python-multipart
supabase
streamlit
```

因为新版 `mediapipe` 会依赖 `opencv-contrib-python`，也可以显式加入：

```text
opencv-contrib-python
```

## 模型文件

需要下载官方模型：

```bash
mkdir -p core_ai/models
curl -L -o core_ai/models/blaze_face_short_range.tflite \
  https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite
```

## `core_ai/face_detector.py` 的目标代码

```python
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


class FaceDetector:
    def __init__(
        self,
        min_detection_confidence=0.5,
        model_path=None,
        input_size=128,
    ):
        """初始化人脸检测器，使用 MediaPipe 官方 BlazeFace 模型。"""
        self.min_detection_confidence = min_detection_confidence
        self.input_size = input_size
        default_model_path = Path(__file__).with_name("models") / "blaze_face_short_range.tflite"
        self.model_path = Path(model_path or default_model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Face detector model not found: {self.model_path}")

        self.net = cv2.dnn.readNetFromTFLite(str(self.model_path))
        self.output_names = self.net.getUnconnectedOutLayersNames()
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

        raw_scores = outputs["classificators"][0, :, 0]
        raw_boxes = outputs["regressors"][0]

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

    @staticmethod
    def _sigmoid(value):
        value = np.clip(value, -100, 100)
        return 1.0 / (1.0 + np.exp(-value))
```

## 测试脚本

`core_ai/test_ai.py`：

```python
from face_detector import FaceDetector
from PIL import Image
import numpy as np

dummy_image = Image.fromarray(np.zeros((500, 500, 3), dtype=np.uint8))
detector = FaceDetector()

print("start detect_faces")
results = detector.detect_faces(dummy_image)

print(f"Detection results: {len(results)}")
print(f"Detection results: {results}")
```

运行：

```bash
python core_ai/test_ai.py
```

预期输出：

```text
start detect_faces
Detection results: 0
Detection results: []
```

## 教学方式

请你按以下顺序教我：

1. 检查虚拟环境和 Python 版本。
2. 检查 `mediapipe` 实际导入路径和版本。
3. 解释为什么新版没有 `mp.solutions`。
4. 下载 BlazeFace 模型。
5. 改写 `face_detector.py`。
6. 运行空白图测试。
7. 用真实人脸图测试。
8. 解释每一段代码在做什么。
9. 帮我把这个能力接入 FastAPI 或 Streamlit。

请不要一次性讲太多。每次只给我一个小步骤和对应命令，等我回复“完成”后再继续。

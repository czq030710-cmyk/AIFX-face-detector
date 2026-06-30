from face_detector import FaceDetector
from PIL import Image
import numpy as np

dummy_image = Image.fromarray(np.zeros((500,500, 3), dtype=np.uint8))
detector = FaceDetector()

print("start detect_faces")
results = detector.detect_faces(dummy_image)

print(f"Detection results: {len(results)}")
print(f"Detection results: {results}")
import cv2
import numpy as np
import onnxruntime as ort
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class YoloInferenceEngine:
    def __init__(self):
        # We only care about people (usually 0 in COCO) and vehicles (e.g., cars 2, trucks 7 in COCO)
        # You will need to adjust these IDs based on the specific YOLOv26 model you are using.
        self.target_classes = {0: "person"}
        self.conf_threshold = 0.5 
        
        try:
            self.session = ort.InferenceSession(settings.MODEL_PATH, providers=["CPUExecutionProvider"])
            self.input_name = self.session.get_inputs()[0].name
            
            # Get the expected input shape from the ONNX model (e.g., 640x640)
            model_shape = self.session.get_inputs()[0].shape
            self.input_h, self.input_w = model_shape[2], model_shape[3]
            
            logger.info(f"ONNX model loaded successfully: {settings.MODEL_PATH} with shape {self.input_w}x{self.input_h}")
        except Exception as e:
            logger.error(f"Failed to load ONNX model from {settings.MODEL_PATH}", exc_info=True)
            raise

    def process_frame(self, frame: np.ndarray) -> list:
        """
        Takes a BGR frame from OpenCV, runs YOLO inference, and returns filtered detections.
        Returns: List of dicts [{"bbox": [x1, y1, x2, y2], "confidence": float, "class_id": int}]
        """
        orig_h, orig_w = frame.shape[:2]
        
        # 1. Preprocessing
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (self.input_w, self.input_h))
        
        tensor = img_resized.astype(np.float32) / 255.0
        tensor = np.transpose(tensor, (2, 0, 1))
        tensor = np.expand_dims(tensor, axis=0)
        
        # 2. Inference
        raw_preds = self.session.run(None, {self.input_name: tensor})[0]

        raw = self.session.run(None, {self.input_name: tensor})

        # print(len(raw))
        # print(raw[0].shape)
        # print(raw[0][0][:10])
        
        # 3. Post-processing & Filtering
        return self._parse_detections(raw_preds, orig_w, orig_h)

    def _parse_detections(self, preds: np.ndarray, orig_w: int, orig_h: int) -> list:
        results = []
        
        # Squeeze batch dimension if present (e.g., from (1, N, 6) to (N, 6))
        if len(preds.shape) == 3:
            preds = np.squeeze(preds, axis=0)
            
        if len(preds) == 0:
            return results

        # 1. Use the exact logic from your old script to filter by confidence
        preds = preds[preds[:, 4] >= self.conf_threshold]
        
        scale_x = orig_w / self.input_w
        scale_y = orig_h / self.input_h

        for row in preds:
            class_id = int(row[5])
            
            # Filter by our target classes (person, car, truck, etc.)
            if class_id not in self.target_classes:
                continue
                
            confidence = float(row[4])
            
            x1 = int(row[0] * scale_x)
            y1 = int(row[1] * scale_y)
            x2 = int(row[2] * scale_x)
            y2 = int(row[3] * scale_y)
            
            results.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": confidence,
                "class_id": class_id,
                "class_name": self.target_classes[class_id]
            })

        return results
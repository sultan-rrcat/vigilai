import cv2
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class VideoCaptureManager:
    def __init__(self):
        self.source = settings.RTSP_URL
        self.stride = settings.FRAME_STRIDE
        self.cap = None

    def start(self):
        """Initializes the video stream."""
        logger.info(f"Connecting to video source: {self.source}")
        self.cap = cv2.VideoCapture(self.source)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video source: {self.source}")
            
        logger.info(f"Successfully connected. Processing every {self.stride}rd/th frame.")

    def get_frames(self):
        """Generates frames based on the configured stride, skipping intermediate frames."""
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("Capture stream is not initialized. Call start() first.")

        frame_idx = 0

        while True:
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning("End of stream or connection lost.")
                break

            # Check if this frame matches our stride pattern
            if frame_idx % self.stride != 0:
                frame_idx += 1
                continue

            frame_idx += 1
            yield frame

    def release(self):
        """Cleans up the capture object."""
        if self.cap:
            self.cap.release()
            logger.info("Video source released.")
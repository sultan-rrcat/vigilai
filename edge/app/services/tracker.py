import logging
from deep_sort_realtime.deepsort_tracker import DeepSort

logger = logging.getLogger(__name__)

class ObjectTracker:
    def __init__(self):
        # max_age: How many frames to wait before dropping a lost track
        # n_init: How many consecutive frames before confirming a track
        self.tracker = DeepSort(
            max_age=15,
            n_init=2,
            nms_max_overlap=0.5,
            max_cosine_distance=0.2,
            embedder="mobilenet", # Lightweight appearance embedding model
            half=True,
            bgr=True,
            embedder_gpu=False # Leave false for Phase 1 local testing
        )
        logger.info("DeepSORT tracker initialized.")

    def update(self, detections: list, frame) -> list:
        """
        Takes YOLO detections and the original frame, updates the Kalman filter
        and Re-ID embeddings, and returns active tracks.
        """
        # deep-sort-realtime expects detections in the format:
        # [ [ [left, top, w, h], confidence, detection_class ], ... ]
        formatted_detections = []
        
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            w = x2 - x1
            h = y2 - y1
            
            formatted_detections.append(
                ([x1, y1, w, h], det["confidence"], det["class_name"])
            )

        # Update the tracker. It uses the frame to generate visual embeddings.
        tracks = self.tracker.update_tracks(formatted_detections, frame=frame)
        
        active_tracks = []
        for track in tracks:
            # Only return tracks that have been consistently seen for `n_init` frames
            if not track.is_confirmed():
                continue
            
            # The Kalman filter predicts the smoothed bounding box
            ltrb = track.to_ltrb() # [left, top, right, bottom]
            
            active_tracks.append({
                "track_id": f"trk_{track.track_id}",
                "bbox": [int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])],
                "class_name": track.get_det_class(),
            })

        return active_tracks
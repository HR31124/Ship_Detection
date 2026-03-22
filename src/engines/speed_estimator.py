from collections import defaultdict, deque
import numpy as np


class SpeedEstimator:
    def __init__(self, fps=30.0, pixel_to_meter=0.05, history_length=12, smoothing_window=5):
        self.fps = fps
        self.scale = pixel_to_meter
        self.history_length = history_length
        self.smoothing_window = max(3, smoothing_window)

        self.centroid_history = defaultdict(lambda: deque(maxlen=history_length))
        self.speeds = {}
        self.speed_history = defaultdict(list)

    def update(self, track_id, bbox):
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        current = np.array([cx, cy])

        hist = self.centroid_history[track_id]

        if len(hist) == 0:
            hist.append(current)
            self.speeds[track_id] = (0.0, 0.0)
            return 0.0, 0.0

        prev = hist[-1]
        distance_px = np.linalg.norm(current - prev)
        dt = 1.0 / self.fps
        speed_px_s = distance_px / dt

        if len(hist) >= 2:
            recent_dists = [
                np.linalg.norm(hist[-i] - hist[-i - 1])
                for i in range(1, min(len(hist), self.smoothing_window))
            ]
            if recent_dists:
                speed_px_s = np.mean(recent_dists) / dt

        speed_m_s = speed_px_s * self.scale
        speed_kmh = speed_m_s * 3.6

        self.speeds[track_id] = (round(speed_px_s, 2), round(speed_kmh, 1))

        if speed_kmh > 0.5:
            self.speed_history[track_id].append(speed_kmh)

        hist.append(current)
        return speed_px_s, speed_kmh

    def get_instant_kmh(self, track_id):
        return self.speeds.get(track_id, (0.0, 0.0))[1]

    def get_average_kmh(self, track_id):
        speeds = self.speed_history.get(track_id, [])
        if not speeds:
            return 0.0
        return round(sum(speeds) / len(speeds), 1)

    def cleanup(self, active_ids):
        to_remove = [tid for tid in list(self.centroid_history) if tid not in active_ids]
        for tid in to_remove:
            self.centroid_history.pop(tid, None)
            self.speeds.pop(tid, None)
            self.speed_history.pop(tid, None)
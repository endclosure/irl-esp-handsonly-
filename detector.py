## THIS IS MADE BY TERRIFIED discord.gg/nixstudios - https://github.com/endclosure

import cv2
import mediapipe as mp

DETECT_WIDTH  = 640
DETECT_HEIGHT = 360
SMOOTH        = 0.5


class PoseDetector:
    def __init__(self):
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._smooth = {}

    def detect(self, frame):
        h, w = frame.shape[:2]

        small = cv2.resize(frame, (DETECT_WIDTH, DETECT_HEIGHT),
                           interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self._hands.process(rgb)

        if not result.multi_hand_landmarks:
            self._smooth.clear()
            return []

        detections = []
        seen = set()

        for hi, hand_lms in enumerate(result.multi_hand_landmarks):
            raw = [(lm.x * w, lm.y * h) for lm in hand_lms.landmark]

            if hi not in self._smooth or len(self._smooth[hi]) != len(raw):
                self._smooth[hi] = raw[:]
            else:
                self._smooth[hi] = [
                    (px * SMOOTH + rx * (1 - SMOOTH),
                     py * SMOOTH + ry * (1 - SMOOTH))
                    for (px, py), (rx, ry) in zip(self._smooth[hi], raw)
                ]
            seen.add(hi)

            pts = [(int(x), int(y)) for x, y in self._smooth[hi]]

            if result.multi_handedness and hi < len(result.multi_handedness):
                label = result.multi_handedness[hi].classification[0].label
            else:
                label = "Hand"

            detections.append({"points": pts, "label": label})

        for hi in list(self._smooth):
            if hi not in seen:
                del self._smooth[hi]

        return detections

    def close(self):
        self._hands.close()
        self._smooth.clear()

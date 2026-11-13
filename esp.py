## THIS IS MADE BY TERRIFIED discord.gg/nixstudios - https://github.com/endclosure

import cv2

CONNECTIONS = [
    (0, 1),  (1, 2),  (2, 3),   (3, 4),
    (0, 5),  (5, 6),  (6, 7),   (7, 8),
    (0, 9),  (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14),(14, 15), (15, 16),
    (0, 17), (17, 18),(18, 19), (19, 20),
    (5, 9),  (9, 13), (13, 17),
]

FINGERTIPS = {4, 8, 12, 16, 20}

PINK  = (245, 187, 253)
WHITE = (245, 245, 245)


def draw_esp(frame, detections, show_box=True, show_skeleton=True):
    if not show_skeleton:
        return frame

    for hand in detections:
        pts = hand["points"]

        for a, b in CONNECTIONS:
            if a < len(pts) and b < len(pts):
                cv2.line(frame, pts[a], pts[b], PINK, 2, cv2.LINE_AA)

        for i, pt in enumerate(pts):
            r = 5 if i in FINGERTIPS else 3
            cv2.circle(frame, pt, r,     WHITE, -1, cv2.LINE_AA)
            cv2.circle(frame, pt, r + 2, PINK,   1, cv2.LINE_AA)

    return frame

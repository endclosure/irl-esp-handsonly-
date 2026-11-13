## THIS IS MADE BY TERRIFIED discord.gg/nixstudios - https://github.com/endclosure

import cv2


def open_camera(index):
    backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
    for backend in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok:
                return cap
        cap.release()
    return None


def list_cameras(max_index=10):
    cameras = []
    for index in range(max_index):
        cap = open_camera(index)
        if cap is not None:
            cameras.append((index, f"Camera {index}"))
            cap.release()
    return cameras


class Camera:
    def __init__(self, index):
        self.cap = open_camera(index)
        if self.cap is None:
            raise RuntimeError(f"Could not open camera {index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        self.cap.set(cv2.CAP_PROP_FPS,          120)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,     1)

    def read(self):
        return self.cap.read()

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

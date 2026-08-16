"""Generate the app icon (1024px PNG, pure numpy+stdlib — no PIL needed).
Dark rounded square, ascending candlesticks. Output: icon_1024.png"""
import os
import struct
import zlib
import numpy as np

S = 1024
img = np.zeros((S, S, 4), np.uint8)

# rounded-square alpha mask (macOS-style, radius ~22.5%)
r = 230
yy, xx = np.mgrid[0:S, 0:S].astype(np.float64)
cx = np.clip(xx, r, S - r)
cy = np.clip(yy, r, S - r)
dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
mask = dist <= r
edge = np.clip(r + 1.5 - dist, 0, 1)  # 1px antialias

# vertical navy gradient background
top = np.array([26, 29, 52], np.float64)
bot = np.array([13, 14, 26], np.float64)
g = (yy / S)[..., None]
img[..., :3] = (top * (1 - g) + bot * g).astype(np.uint8)

# subtle grid lines
for gy in range(220, S - 100, 160):
    img[gy:gy + 3, :, :3] = (img[gy:gy + 3, :, :3] * 0.82 + np.array([60, 66, 100]) * 0.18).astype(np.uint8)


def rect(x0, y0, x1, y1, color):
    x0, x1 = max(0, x0), min(S, x1)
    y0, y1 = max(0, y0), min(S, y1)
    img[y0:y1, x0:x1, :3] = color


GREEN = np.array([64, 208, 130], np.uint8)
RED = np.array([238, 96, 96], np.uint8)
# ascending candles: (x_left, body_top, body_bottom, color); width 118, wick 16
CANDLES = [
    (128, 620, 800, GREEN),
    (306, 668, 560, RED),      # one red pullback (top>bottom handled below)
    (484, 430, 640, GREEN),
    (662, 330, 520, GREEN),
    (840, 200, 420, GREEN),
]
for cxl, t, b, col in CANDLES:
    t, b = min(t, b), max(t, b)
    rect(cxl + 51, t - 55, cxl + 67, b + 55, col)  # wick
    rect(cxl, t, cxl + 118, b, col)                 # body

# apply rounded mask with antialiased edge
img[..., 3] = (edge * 255).astype(np.uint8)
img[~mask & (edge <= 0)] = 0


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


raw = b"".join(b"\x00" + img[i].tobytes() for i in range(S))
png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", S, S, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw, 9))
       + chunk(b"IEND", b""))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon_1024.png")
with open(out, "wb") as fh:
    fh.write(png)
print(f"wrote {out}")

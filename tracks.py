#!/usr/bin/env python3
"""Render an aircraft's ADS-B track as a PNG. Pure stdlib - no matplotlib, no Pillow."""
import json, math, struct, zlib, urllib.request

W, H, PAD = 1000, 700, 60
BG, GRID = (14, 18, 26), (30, 38, 52)


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h, self.px = w, h, bytearray(bg * w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def dot(self, x, y, c, r=1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    self.set(x + dx, y + dy, c)

    def line(self, x0, y0, x1, y1, c, width=3):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(steps + 1):
            t = i / steps
            self.dot(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c, width // 2)

    def png(self, path):
        raw = b"".join(b"\x00" + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3])
                       for y in range(self.h))

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)))
            f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
            f.write(chunk(b"IEND", b""))


def alt_color(alt, lo, hi):
    if not isinstance(alt, (int, float)):
        return (240, 200, 80)
    t = 0.0 if hi <= lo else max(0.0, min(1.0, (alt - lo) / (hi - lo)))
    return (round(250 - 170 * t), round(180 + 40 * t), round(70 + 170 * t))


def fetch_trace(hexid):
    hexid = hexid.lower()
    url = f"https://globe.adsb.lol/data/traces/{hexid[-2:]}/trace_recent_{hexid}.json"
    req = urllib.request.Request(url, headers={
        "User-Agent": "flight-alerts/1.0", "Referer": "https://globe.adsb.lol/",
        "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
        return json.loads(data)


def path_complexity(pts):
    """Path length / bounding-box diagonal. High = convoluted (sky-drawing, survey)."""
    if len(pts) < 10:
        return 0.0
    path = sum(math.dist(pts[i][:2], pts[i + 1][:2]) for i in range(len(pts) - 1))
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    diag = math.dist((min(lats), min(lons)), (max(lats), max(lons)))
    return path / diag if diag > 1e-9 else 0.0


def render(hexid, out):
    """Returns (path, complexity) or (None, 0) if not enough track."""
    try:
        d = fetch_trace(hexid)
    except Exception:
        return None, 0.0
    pts = [(p[1], p[2], p[3]) for p in d.get("trace", [])
           if p[1] is not None and p[2] is not None]
    if len(pts) < 2:
        return None, 0.0

    cx = path_complexity(pts)
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    alts = [p[2] for p in pts if isinstance(p[2], (int, float))] or [0]
    kx = math.cos(math.radians((min(lats) + max(lats)) / 2))
    xs = [lo * kx for lo in lons]
    x0, x1, y0, y1 = min(xs), max(xs), min(lats), max(lats)
    span = max(x1 - x0, y1 - y0, 1e-4)

    def proj(lat, lon):
        px = PAD + (W - 2 * PAD) * (((lon * kx) - x0) / span) \
             + (W - 2 * PAD) * (1 - (x1 - x0) / span) / 2
        py = H - PAD - (H - 2 * PAD) * ((lat - y0) / span) \
             - (H - 2 * PAD) * (1 - (y1 - y0) / span) / 2
        return px, py

    c = Canvas(W, H, BG)
    for gx in range(PAD, W - PAD + 1, (W - 2 * PAD) // 6):
        for y in range(PAD, H - PAD):
            c.set(gx, y, GRID)
    for gy in range(PAD, H - PAD + 1, (H - 2 * PAD) // 4):
        for x in range(PAD, W - PAD):
            c.set(x, gy, GRID)

    lo, hi = min(alts), max(alts)
    prev = None
    for lat, lon, alt in pts:
        p = proj(lat, lon)
        if prev:
            c.line(prev[0], prev[1], p[0], p[1], alt_color(alt, lo, hi), 3)
        prev = p

    s, e = proj(pts[0][0], pts[0][1]), proj(pts[-1][0], pts[-1][1])
    c.dot(round(s[0]), round(s[1]), (120, 130, 150), 5)
    c.dot(round(e[0]), round(e[1]), (255, 255, 255), 8)
    c.dot(round(e[0]), round(e[1]), (255, 60, 60), 5)
    c.png(out)
    return out, cx

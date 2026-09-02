# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Rayala
#!/usr/bin/env python3
"""Realistic top-down sprite generator for the 1942 kitty-graphics layer.
Minimal PNG writer (zlib only), no external deps. Draws WWII-style aircraft
seen from above — fuselage, swept wings, canopy, spinning-prop disc — so each
sprite reads as what it is. Transparent background, RGBA8."""
import zlib, struct, os, sys, math

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets"
os.makedirs(OUT, exist_ok=True)


# ---- canvas + compositing -------------------------------------------------
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [(0, 0, 0, 0)] * (w * h)

    def over(self, x, y, c):
        # source-over alpha composite (c may be translucent, for glow/prop)
        x, y = int(x), int(y)
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        if len(c) == 3:
            c = (c[0], c[1], c[2], 255)
        sr, sg, sb, sa = c
        if sa == 0:
            return
        if sa == 255:
            self.px[y * self.w + x] = c
            return
        dr, dg, db, da = self.px[y * self.w + x]
        a = sa / 255.0
        nr = int(sr * a + dr * (1 - a))
        ng = int(sg * a + dg * (1 - a))
        nb = int(sb * a + db * (1 - a))
        na = int(sa + da * (1 - a))
        self.px[y * self.w + x] = (nr, ng, nb, min(255, na))


def write_png(path, cv):
    w, h = cv.w, cv.h
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw += bytes(cv.px[y * w + x])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(chunk(b"IEND", b""))


# ---- primitives -----------------------------------------------------------
def ellipse(cv, cx, cy, rx, ry, c):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            if rx <= 0 or ry <= 0:
                continue
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0:
                cv.over(x, y, c)


def circle(cv, cx, cy, r, c):
    ellipse(cv, cx, cy, r, r, c)


def poly(cv, pts, c):
    ys = [p[1] for p in pts]
    y0, y1 = int(math.floor(min(ys))), int(math.ceil(max(ys)))
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        yc = y + 0.5
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if (ay <= yc < by) or (by <= yc < ay):
                xs.append(ax + (bx - ax) * (yc - ay) / (by - ay))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(int(math.floor(xs[k])), int(math.ceil(xs[k + 1]))):
                cv.over(x, y, c)


def vflip(cv):
    out = Canvas(cv.w, cv.h)
    for y in range(cv.h):
        for x in range(cv.w):
            out.px[(cv.h - 1 - y) * cv.w + x] = cv.px[y * cv.w + x]
    return out


# ---- an aircraft, seen from above, nose UP (north) ------------------------
def fighter(W, H, pal, wing_span=0.94, wing_sweep=0.10, tail=True,
            roundel=None, engines=0, twin_tail=False):
    cv = Canvas(W, H)
    cx = W / 2
    base, shade, light = pal["base"], pal["shade"], pal["light"]
    canopy = pal["canopy"]
    nose = pal.get("nose", shade)

    # spinning-prop disc (translucent) at the very nose — a flat wide blur, so
    # it reads as a propeller rather than a mast
    prop = (205, 208, 212, 110)
    ellipse(cv, cx, H * 0.085, W * 0.20, H * 0.022, prop)
    ellipse(cv, cx, H * 0.085, W * 0.03, H * 0.035, (205, 208, 212, 70))

    # main wing: swept-back hexagon meeting at a center ridge
    wl = W * (1 - wing_span) / 2
    wr = W - wl
    wy = H * 0.50
    sweep = H * wing_sweep
    poly(cv, [(cx, wy - H * 0.05), (wl, wy + sweep), (wl, wy + sweep + H * 0.045),
              (cx, wy + H * 0.11), (wr, wy + sweep + H * 0.045), (wr, wy + sweep)],
         base)
    # wing tips + trailing-edge shading
    poly(cv, [(cx, wy + H * 0.06), (wl, wy + sweep + H * 0.02),
              (wl, wy + sweep + H * 0.045), (cx, wy + H * 0.11),
              (wr, wy + sweep + H * 0.045), (wr, wy + sweep + H * 0.02)], shade)

    # engine nacelles on the wings (for the boss/bomber)
    if engines:
        for s in range(engines):
            frac = (s + 1) / (engines + 1)
            ex = wl + (wr - wl) * frac
            if abs(ex - cx) < W * 0.10:
                continue
            ellipse(cv, ex, wy + sweep * 0.6, W * 0.035, H * 0.11, shade)
            ellipse(cv, ex, wy + sweep * 0.6 - H * 0.02, W * 0.03, H * 0.05, nose)
            ellipse(cv, ex, wy + sweep * 0.6 - H * 0.05, W * 0.05, H * 0.012,
                    (205, 208, 212, 120))

    # roundels (rising-sun style) on each wing
    if roundel:
        for s in (-1, 1):
            rx = cx + s * W * 0.28
            circle(cv, rx, wy + sweep + H * 0.01, W * 0.055, (235, 235, 230, 255))
            circle(cv, rx, wy + sweep + H * 0.01, W * 0.038, roundel)

    # fuselage (long vertical body) with a lighter dorsal spine
    ellipse(cv, cx, H * 0.50, W * 0.085, H * 0.40, base)
    # dorsal spine highlight
    ellipse(cv, cx - W * 0.012, H * 0.46, W * 0.03, H * 0.30, light)
    # fuselage outline shade on the right
    ellipse(cv, cx + W * 0.055, H * 0.52, W * 0.03, H * 0.34, shade)

    # nose cone / spinner
    ellipse(cv, cx, H * 0.135, W * 0.055, H * 0.075, nose)

    # tailplane (horizontal stabilizer near the tail)
    if tail:
        ty = H * 0.85
        poly(cv, [(cx, ty - H * 0.03), (cx - W * 0.24, ty + H * 0.02),
                  (cx - W * 0.24, ty + H * 0.04), (cx, ty + H * 0.05),
                  (cx + W * 0.24, ty + H * 0.04), (cx + W * 0.24, ty + H * 0.02)],
             base)
    if twin_tail:
        for s in (-1, 1):
            ellipse(cv, cx + s * W * 0.22, H * 0.88, W * 0.03, H * 0.06, shade)

    # canopy (cockpit glass) with a glint
    ellipse(cv, cx, H * 0.42, W * 0.05, H * 0.085, canopy)
    ellipse(cv, cx - W * 0.015, H * 0.40, W * 0.02, H * 0.03,
            (255, 255, 255, 150))
    return cv


# ---- palettes -------------------------------------------------------------
GREEN = dict(base=(58, 150, 66), shade=(30, 96, 40), light=(150, 220, 140),
             canopy=(95, 170, 225), nose=(55, 60, 62))
GRAY = dict(base=(156, 158, 148), shade=(96, 98, 92), light=(210, 212, 205),
            canopy=(70, 105, 80), nose=(72, 72, 76))
TEAL = dict(base=(66, 178, 200), shade=(30, 108, 128), light=(160, 232, 242),
            canopy=(30, 66, 86), nose=(40, 46, 56))
RED = dict(base=(206, 58, 52), shade=(120, 26, 24), light=(242, 150, 130),
           canopy=(250, 214, 96), nose=(250, 200, 80))
IRON = dict(base=(150, 44, 42), shade=(92, 22, 22), light=(206, 96, 82),
            canopy=(70, 210, 224), nose=(60, 62, 68))
ROUNDEL_RED = (208, 42, 40, 255)


def power_gem(W, H):
    """A collectible weapon power-up: a glowing faceted gem with a star glint."""
    cv = Canvas(W, H)
    cx, cy = W / 2, H / 2
    # soft outer glow
    for r, a in ((0.50, 40), (0.42, 70), (0.34, 110)):
        ellipse(cv, cx, cy, W * r, H * r, (255, 180, 70, a))
    # faceted diamond body (gold)
    dia = [(cx, cy - H * 0.40), (cx + W * 0.34, cy), (cx, cy + H * 0.40),
           (cx - W * 0.34, cy)]
    poly(cv, dia, (255, 196, 54, 255))
    # inner facet shading (right/bottom darker, left/top lighter)
    poly(cv, [(cx, cy - H * 0.40), (cx + W * 0.34, cy), (cx, cy)], (230, 150, 30, 255))
    poly(cv, [(cx, cy + H * 0.40), (cx + W * 0.34, cy), (cx, cy)], (200, 120, 20, 255))
    poly(cv, [(cx, cy + H * 0.40), (cx - W * 0.34, cy), (cx, cy)], (240, 170, 40, 255))
    # bright core + star glint
    circle(cv, cx, cy, W * 0.10, (255, 246, 210, 255))
    for dx, dy, ln in ((1, 0, 0.22), (-1, 0, 0.22), (0, 1, 0.26), (0, -1, 0.26)):
        for t in range(1, 12):
            f = t / 12.0
            cv.over(cx + dx * W * ln * f, cy + dy * H * ln * f,
                    (255, 255, 255, int(220 * (1 - f))))
    return cv


# ---- build ----------------------------------------------------------------
# Player fighter: nose up (flies north).
write_png(f"{OUT}/fighter.png", fighter(40, 40, GREEN, wing_span=0.94,
          wing_sweep=0.06, roundel=(230, 230, 235, 255)))
# Zeros dive at you: nose down, with rising-sun roundels.
write_png(f"{OUT}/zero.png", vflip(fighter(40, 40, GRAY, wing_span=0.92,
          wing_sweep=0.05, roundel=ROUNDEL_RED)))
# Weaver: a slim swept interceptor, nose down.
write_png(f"{OUT}/weaver.png", vflip(fighter(40, 40, TEAL, wing_span=0.80,
          wing_sweep=0.20, roundel=ROUNDEL_RED)))
# Red leader: heavier, yellow-nosed, nose down.
write_png(f"{OUT}/leader.png", vflip(fighter(40, 40, RED, wing_span=0.98,
          wing_sweep=0.12, roundel=ROUNDEL_RED)))
# Boss carrier: a big four-engine bomber with twin tail, cyan reactor, nose down.
write_png(f"{OUT}/boss.png", vflip(fighter(72, 48, IRON, wing_span=0.99,
          wing_sweep=0.10, engines=4, twin_tail=True, roundel=ROUNDEL_RED)))
# Weapon power-up: a glowing gem.
write_png(f"{OUT}/power.png", power_gem(36, 36))

for n in ("fighter", "zero", "weaver", "leader", "power", "boss"):
    p = f"{OUT}/{n}.png"
    print(f"{p}: {os.path.getsize(p)} bytes")

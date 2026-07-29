#!/usr/bin/env python3
"""
Bytebeat player + fullscreen X11 overlay visualizer.
Draws directly on root window (like GDI malware on Windows).
Requires: X11, pulseaudio/pipewire (pactl), python3-xlib, numpy
Install: pip install python-xlib numpy
"""

import sys, os, time, threading, struct, math
from ctypes import CDLL, c_int, c_uint, c_ulong, c_char_p, c_void_p, POINTER, Structure, byref

# ---- Bytebeat generators ----
BYTEBEATS = {
    "classic":    lambda t: (t * (t >> 8 | t >> 9) & 46 & t >> 8) ^ (t & t >> 13 | t >> 6),
    "kick":       lambda t: (t * (t >> 11 & t >> 8 & 123 & t >> 3)) ^ (t & t >> 14),
    "acid":       lambda t: (t | (t >> 9 | t >> 7)) * t & (t >> 11 | t >> 9),
    "glitch":     lambda t: (t ^ t >> 3 | t >> 5) * (t & t >> 10),
    "melodic":    lambda t: int((math.sin(t * 0.0001) * 127 + 128) * (t & t >> 8)),
    "noise":      lambda t: (t * (t >> 5 | t >> 8)) & (t >> 16),
}

# ---- Audio (PulseAudio/PipeWire via pactl) ----
SAMPLE_RATE = 8000  # bytebeat standard
CHANNELS = 1
FORMAT = "s16le"  # 16-bit signed little-endian

def bytebeat_to_pcm(func, duration_sec=60):
    """Generate PCM bytes from bytebeat function."""
    import numpy as np
    samples = int(SAMPLE_RATE * duration_sec)
    t = np.arange(samples, dtype=np.uint32)
    vals = func(t)
    # Convert to signed 16-bit
    vals = ((vals & 0xFF).astype(np.int16) - 128) * 256
    return vals.tobytes()

def play_audio(pcm_bytes):
    """Stream PCM to PulseAudio/PipeWire via pactl."""
    import subprocess
    cmd = ["pactl", "load-module", "module-pipe-sink",
           f"file=/tmp/bytebeat_sink", f"format={FORMAT}", f"rate={SAMPLE_RATE}", f"channels={CHANNELS}"]
    subprocess.run(cmd, capture_output=True)
    time.sleep(0.2)
    try:
        with open("/tmp/bytebeat_sink", "wb") as f:
            f.write(pcm_bytes)
    finally:
        subprocess.run(["pactl", "unload-module", "module-pipe-sink"], capture_output=True)

# ---- X11 Overlay (draw on root window) ----
class X11Overlay:
    def __init__(self):
        self.xlib = CDLL("libX11.so.6")
        self.dpy = self.xlib.XOpenDisplay(None)
        if not self.dpy:
            raise RuntimeError("Cannot open X display")
        self.screen = self.xlib.XDefaultScreen(self.dpy)
        self.root = self.xlib.XRootWindow(self.dpy, self.screen)
        self.width = self.xlib.XDisplayWidth(self.dpy, self.screen)
        self.height = self.xlib.XDisplayHeight(self.dpy, self.screen)

        # Create GC
        self.gc = self.xlib.XCreateGC(self.dpy, self.root, 0, None)
        self.xlib.XSetForeground(self.dpy, self.gc, 0xFFFFFF)
        self.xlib.XSetBackground(self.dpy, self.gc, 0x000000)
        self.xlib.XSetLineAttributes(self.dpy, self.gc, 1, 0, 0, 0)  # solid, thin

        # Clear root
        self.xlib.XClearWindow(self.dpy, self.root)

    def draw_pixel(self, x, y, color):
        self.xlib.XSetForeground(self.dpy, self.gc, color)
        self.xlib.XDrawPoint(self.dpy, self.root, self.gc, x, y)

    def draw_line(self, x1, y1, x2, y2, color):
        self.xlib.XSetForeground(self.dpy, self.gc, color)
        self.xlib.XDrawLine(self.dpy, self.root, self.gc, x1, y1, x2, y2)

    def draw_rect(self, x, y, w, h, color, filled=False):
        self.xlib.XSetForeground(self.dpy, self.gc, color)
        if filled:
            self.xlib.XFillRectangle(self.dpy, self.root, self.gc, x, y, w, h)
        else:
            self.xlib.XDrawRectangle(self.dpy, self.root, self.gc, x, y, w, h)

    def clear(self):
        self.xlib.XClearWindow(self.dpy, self.root)

    def flush(self):
        self.xlib.XFlush(self.dpy)

    def close(self):
        self.xlib.XFreeGC(self.dpy, self.gc)
        self.xlib.XCloseDisplay(self.dpy)


# ---- Visualizer ----
class Visualizer:
    def __init__(self, overlay, beat_func):
        self.overlay = overlay
        self.beat_func = beat_func
        self.t = 0
        self.running = True
        self.particles = []

    def hsv_to_rgb(self, h, s, v):
        h = h % 1.0
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        if i == 0: r, g, b = v, t, p
        elif i == 1: r, g, b = q, v, p
        elif i == 2: r, g, b = p, v, t
        elif i == 3: r, g, b = p, q, v
        elif i == 4: r, g, b = t, p, v
        else: r, g, b = v, p, q
        return int(r*255)<<16 | int(g*255)<<8 | int(b*255)

    def step(self):
        w, h = self.overlay.width, self.overlay.height
        cx, cy = w // 2, h // 2

        # Generate a few bytebeat values for visual sync
        val = self.beat_func(self.t) & 0xFF
        self.t += 1

        # Clear with fade trail
        self.overlay.xlib.XSetForeground(self.overlay.dpy, self.overlay.gc, 0x000000)
        self.overlay.xlib.XFillRectangle(self.overlay.dpy, self.overlay.root, self.overlay.gc, 0, 0, w, h)

        # Center pulse
        radius = 50 + (val * 3)
        color = self.hsv_to_rgb(self.t * 0.001, 0.8, 1.0)
        self.overlay.draw_rect(cx - radius//2, cy - radius//2, radius, radius, color, filled=True)

        # Radial lines
        for i in range(16):
            angle = (self.t * 0.01) + i * (2*math.pi/16)
            r1 = radius
            r2 = radius + 100 + (val * 2)
            x1 = cx + int(r1 * math.cos(angle))
            y1 = cy + int(r1 * math.sin(angle))
            x2 = cx + int(r2 * math.cos(angle))
            y2 = cy + int(r2 * math.sin(angle))
            self.overlay.draw_line(x1, y1, x2, y2, color)

        # Particles from beat
        if val > 200:
            for _ in range(5):
                self.particles.append({
                    'x': cx + random.randint(-50, 50),
                    'y': cy + random.randint(-50, 50),
                    'vx': random.uniform(-5, 5),
                    'vy': random.uniform(-5, 5),
                    'life': 60,
                    'color': self.hsv_to_rgb(random.random(), 1.0, 1.0)
                })

        for p in self.particles[:]:
            self.overlay.draw_rect(int(p['x']), int(p['y']), 3, 3, p['color'], filled=True)
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            p['vy'] += 0.1  # gravity
            if p['life'] <= 0:
                self.particles.remove(p)

        # Waveform bars at bottom
        for i in range(64):
            sample_t = self.t + i * 100
            v = self.beat_func(sample_t) & 0xFF
            bar_h = int(v * h / 256 * 0.3)
            x = i * (w // 64)
            y = h - bar_h
            c = self.hsv_to_rgb(i/64 + self.t*0.001, 0.7, 1.0)
            self.overlay.draw_rect(x, y, w//64 - 2, bar_h, c, filled=True)

        self.overlay.flush()

    def run(self):
        while self.running:
            self.step()
            time.sleep(1/60)  # 60 FPS


import random

def main():
    if "DISPLAY" not in os.environ:
        print("Error: No X11 display. Run under X11 (not Wayland).")
        sys.exit(1)

    print("Bytebeat options:", list(BYTEBEATS.keys()))
    name = sys.argv[1] if len(sys.argv) > 1 else "classic"
    if name not in BYTEBEATS:
        name = "classic"
    print(f"Playing: {name}")

    # Generate audio
    print("Generating audio...")
    import numpy as np
    func = BYTEBEATS[name]
    pcm = bytebeat_to_pcm(func, duration_sec=300)  # 5 min loop

    # Start audio thread
    audio_thread = threading.Thread(target=play_audio, args=(pcm,), daemon=True)
    audio_thread.start()

    # Start visualizer
    print("Starting overlay (press Ctrl+C to quit)...")
    overlay = X11Overlay()
    viz = Visualizer(overlay, func)
    try:
        viz.run()
    except KeyboardInterrupt:
        pass
    finally:
        overlay.clear()
        overlay.flush()
        overlay.close()
        print("\nDone.")

if __name__ == "__main__":
    main()
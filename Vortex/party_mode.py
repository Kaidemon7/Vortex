#!/usr/bin/env python3
"""
Party Mode - Bytebeat Visualizer for Linux X11
Plays bytebeat audio via PulseAudio/PipeWire, draws on root X11 window.
"""

import sys
import os
import math
import time
import threading
import random
import signal

try:
    from Xlib import display, X, XK, xtest
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

SAMPLE_RATE = 44100
CHUNK_SIZE = 1024

# Global state
t = 0
running = True
phase = 0
mouse_pos = (0, 0)
party_text_drawn = False

# Visual objects
balls = []
disco_balls = []
rainbow_lines = []


def bytebeat1(t):
    """Phase 1: balls & disco"""
    return (
        (t * (1 + '4451'[t >> 13 & 3] / 10) & t >> 9) +
        (.003 * t & 3)
    ) & 255


def bytebeat2(t):
    """Phase 2: balls & disco keep going"""
    return (
        (pow(2.75, -t / 2048 % 8 + 8) & 128) +
        (t * (t & t >> 11) & 64) |
        t / [2, 2, 2, 2, 3, 3, 4, 4][(t >> 14) % 8] & 128
    ) & 255


def bytebeat3(t):
    """Phase 3: takes mouse control, draws PARTY MODE once"""
    return (
        (((t >> 4) >> (t & (t >> 11))) *
         (((t >> 4) >> (t & (t >> 11))) & 128 and -1 or 1)) +
        (t >> t / (t & 65536 and 2 or 3) & 63) +
        (30000 / (t & 4095) & 100)
    ) & 255


def hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t_val = v * (1 - (1 - f) * s)
    if i == 0:
        r, g, b = v, t_val, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t_val
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t_val, p, v
    else:
        r, g, b = v, p, q
    return int(r * 255) << 16 | int(g * 255) << 8 | int(b * 255)


class AudioThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paUInt8,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        )

    def run(self):
        global t, running, phase
        while running:
            buf = bytearray(CHUNK_SIZE)
            for i in range(CHUNK_SIZE):
                if phase == 0:
                    val = int(bytebeat1(t)) & 255
                elif phase == 1:
                    val = int(bytebeat2(t)) & 255
                else:
                    val = int(bytebeat3(t)) & 255
                buf[i] = val
                t += 1
            try:
                self.stream.write(bytes(buf))
            except:
                break

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


class X11Visual:
    def __init__(self):
        self.d = display.Display()
        self.screen = self.d.screen()
        self.root = self.screen.root
        self.gc = self.root.create_gc(
            foreground=self.screen.white_pixel,
            background=self.screen.black_pixel
        )
        self.width = self.screen.width_in_pixels
        self.height = self.screen.height_in_pixels
        self.disco_angle = 0

    def draw_ball(self, x, y, r, color):
        self.d.change_gc(self.gc, foreground=color)
        self.root.poly_fill_arc(
            self.gc, x - r, y - r, r * 2, r * 2, 0, 360 * 64
        )

    def draw_disco_ball(self, x, y, r, t):
        self.disco_angle += 0.05
        for i in range(12):
            angle = self.disco_angle + i * math.pi / 6
            x1 = int(x + math.cos(angle) * r * 0.3)
            y1 = int(y + math.sin(angle) * r * 0.3)
            x2 = int(x + math.cos(angle) * r)
            y2 = int(y + math.sin(angle) * r)
            color = hsv_to_rgb(i / 12 + t * 0.001, 1.0, 1.0)
            self.d.change_gc(self.gc, foreground=color)
            self.root.poly_line(self.gc, X.CoordModeOrigin, [(x1, y1), (x2, y2)])

    def draw_rainbow_line(self, x1, y1, x2, y2, t):
        self.d.change_gc(self.gc, foreground=hsv_to_rgb(t * 0.01, 1.0, 1.0))
        self.root.poly_line(self.gc, X.CoordModeOrigin, [(x1, y1), (x2, y2)])

    def clear(self):
        self.d.change_gc(self.gc, foreground=0x000000)
        self.root.poly_fill_rectangle(self.gc, [(0, 0, self.width, self.height)])

    def flush(self):
        self.d.flush()

    def close(self):
        self.clear()
        self.d.flush()
        self.d.free_gc(self.gc)
        self.d.close()


visual = None


def init_visual():
    global visual
    if visual is None:
        visual = X11Visual()


def phase1_visual():
    global balls, disco_balls, t, visual, running
    init_visual()

    visual.clear()

    # Spawn disco balls periodically
    if t % 500 == 0 and len(disco_balls) < 15:
        disco_balls.append({
            'x': random.randint(50, visual.width - 50),
            'y': random.randint(50, visual.height - 50),
            'r': random.randint(30, 80),
        })

    # Draw disco balls
    for ball in disco_balls:
        visual.draw_disco_ball(ball['x'], ball['y'], ball['r'], t)

    # Spawn flashing balls
    if t % 100 == 0 and len(balls) < 50:
        balls.append({
            'x': random.randint(0, visual.width),
            'y': random.randint(0, visual.height),
            'r': random.randint(5, 20),
            'color': hsv_to_rgb(random.random(), 1.0, 1.0),
            'life': 120,
            'vx': random.uniform(-3, 3),
            'vy': random.uniform(-3, 3)
        })

    # Update and draw balls
    for ball in balls[:]:
        visual.draw_ball(int(ball['x']), int(ball['y']), ball['r'], ball['color'])
        ball['x'] += ball['vx']
        ball['y'] += ball['vy']
        ball['vy'] += 0.1
        ball['life'] -= 1
        if ball['life'] <= 0 or ball['x'] < -50 or ball['x'] > visual.width + 50:
            balls.remove(ball)

    visual.flush()


def phase2_visual():
    global balls, disco_balls, rainbow_lines, mouse_pos, t, visual, running
    init_visual()

    visual.clear()

    # Get mouse position
    try:
        pointer = visual.root.query_pointer()
        mouse_pos = (pointer.root_x, pointer.root_y)
    except:
        pass

    # Draw disco balls
    for ball in disco_balls:
        visual.draw_disco_ball(ball['x'], ball['y'], ball['r'], t)

    # Draw bouncing balls
    for ball in balls[:]:
        visual.draw_ball(int(ball['x']), int(ball['y']), ball['r'], ball['color'])
        ball['x'] += ball['vx']
        ball['y'] += ball['vy']
        ball['vy'] += 0.1
        ball['life'] -= 1
        if ball['life'] <= 0:
            balls.remove(ball)

    # Spawn new balls
    if t % 80 == 0 and len(balls) < 80:
        balls.append({
            'x': random.randint(0, visual.width),
            'y': random.randint(0, visual.height),
            'r': random.randint(5, 20),
            'color': hsv_to_rgb(random.random(), 1.0, 1.0),
            'life': 120,
            'vx': random.uniform(-3, 3),
            'vy': random.uniform(-3, 3)
        })

    # Mini disco ball follows mouse
    if mouse_pos:
        mx, my = mouse_pos
        visual.draw_disco_ball(mx, my, 40, t)

    # Rainbow lines from center
    cx, cy = visual.width // 2, visual.height // 2
    for i in range(16):
        angle = t * 0.01 + i * (2 * math.pi / 16)
        x2 = cx + int(visual.width * 0.6 * math.cos(angle))
        y2 = cy + int(visual.height * 0.6 * math.sin(angle))
        visual.draw_rainbow_line(cx, cy, x2, y2, t)

    visual.flush()


def phase3_visual():
    global t, party_text_drawn, visual, running, mouse_pos
    init_visual()

    visual.clear()

    # Draw PARTY MODE text once
    if not party_text_drawn:
        party_text_drawn = True

    cx, cy = visual.width // 2, visual.height // 2
    text = "PARTY MODE"
    # Draw using simple dots for each character
    for i, ch in enumerate(text):
        x = cx - len(text) * 12 + i * 24
        y = cy
        color = hsv_to_rgb(i / len(text) + t * 0.01, 1.0, 1.0)
        visual.d.change_gc(visual.gc, foreground=color)
        visual.root.poly_point(
            visual.gc, X.CoordModeOrigin,
            [(x + dx, y + dy) for dx in range(16) for dy in range(16) if random.random() < 0.3]
        )

    # Take mouse control - warp to center
    if t % 60 == 0:
        try:
            xtest.fake_input(visual.d, X.MotionNotify, x=visual.width // 2, y=visual.height // 2)
            visual.d.flush()
        except:
            pass

    visual.flush()


def visual_loop():
    global phase, running, visual, t
    init_visual()

    try:
        while running:
            if phase == 0:
                phase1_visual()
            elif phase == 1:
                phase2_visual()
            else:
                phase3_visual()
            time.sleep(1 / 60)
    except KeyboardInterrupt:
        pass
    finally:
        visual.clear()
        visual.flush()
        visual.close()


class MouseThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.d = display.Display()
        self.screen = self.d.screen()
        self.root = self.screen.root

    def run(self):
        global mouse_pos, running
        while running:
            try:
                pointer = self.root.query_pointer()
                mouse_pos = (pointer.root_x, pointer.root_y)
            except:
                pass
            time.sleep(1 / 60)

    def stop(self):
        self.d.close()


class PhaseController(threading.Thread):
    def run(self):
        global phase, running, party_text_drawn
        time.sleep(60)
        if running:
            phase = 1
            print("\n>>> PHASE 2: Rainbow lines + mouse disco")
        time.sleep(60)
        if running:
            phase = 2
            party_text_drawn = False
            print("\n>>> PHASE 3: Mouse control + PARTY MODE text")
        time.sleep(30)
        if running:
            running = False


def check_deps():
    if not HAS_XLIB:
        print("Missing: python-xlib (pip install python-xlib)")
        return False
    if not HAS_PYAUDIO:
        print("Missing: pyaudio (pip install pyaudio)")
        return False
    return True


def signal_handler(sig, frame):
    global running
    running = False
    sys.exit(0)


def main():
    if "DISPLAY" not in os.environ:
        print("Error: No X11 display. Run under X11 (not Wayland).")
        sys.exit(1)

    if not check_deps():
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🎉 PARTY MODE STARTING")
    print("Phase 1 (60s): Balls & Disco - bytebeat 1")
    print("Phase 2 (60s): Balls + Disco + Mouse Disco + Rainbow Lines - bytebeat 2")
    print("Phase 3 (30s): Mouse Control + PARTY MODE text - bytebeat 3")
    print("Press Ctrl+C to stop at any time")
    print()

    audio = AudioThread()
    audio.start()

    mouse = MouseThread()
    mouse.start()

    controller = PhaseController()
    controller.start()

    try:
        visual_loop()
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        audio.stop()
        mouse.stop()
        print("\n🎉 PARTY MODE STOPPED")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Party Mode - Bytebeat Visualizer for Linux (X11 + Wayland via XWayland)
Creates a fullscreen transparent window for visuals, plays bytebeat audio.
Press Ctrl+C in this terminal to stop at any time.
"""

import sys
import os
import math
import time
import threading
import random
import signal

# Try Qt first (works on both X11 and Wayland)
try:
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtCore import Qt, QTimer, QPoint
    from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
    HAS_QT = True
except ImportError:
    HAS_QT = False

# Fallback to Xlib (X11 only)
try:
    from Xlib import display, X, xtest
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


def bytebeat1(t):
    """Phase 1: balls & disco - t*(1+'4451'[t>>13&3]/10)&t>>9+(.003*t&3)"""
    idx = (t >> 13) & 3
    mult = 1 + int('4451'[idx]) / 10
    return int(t * mult) & (t >> 9) + int(.003 * t & 3)


def bytebeat2(t):
    """Phase 2: balls & disco keep going - (pow(2.75,-t/2048%8+8)&128)+(t*(t&t>>11)&64)|t/[2,2,2,2,3,3,4,4][(t>>14)%8]&128"""
    arr = [2, 2, 2, 2, 3, 3, 4, 4]
    div = arr[(t >> 14) % 8]
    part1 = int(pow(2.75, -t / 2048 % 8 + 8)) & 128
    part2 = (t * (t & (t >> 11)) & 64)
    part3 = (t // div) & 128
    return (part1 + part2) | part3


def bytebeat3(t):
    """Phase 3: takes mouse control, draws PARTY MODE once"""
    shift = t & (t >> 11)
    inner = (t >> 4) >> shift
    sign = -1 if (inner & 128) else 1
    part1 = inner * sign
    div = 2 if (t & 65535) else 3
    part2 = (t >> (t // div)) & 63
    part3 = int(30000 / (t & 4095)) & 100
    return (part1 + part2 + part3) & 255


def hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    tt = v * (1 - (1 - f) * s)
    if i == 0:
        r, g, b = v, tt, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, tt
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = tt, p, v
    else:
        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


# ============================================================
# Audio Thread (same for both backends)
# ============================================================
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


# ============================================================
# Qt Backend (Works on X11 + Wayland via XWayland)
# ============================================================
class QtVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        screen = QApplication.primaryScreen()
        self.resize(screen.size())
        self.showFullScreen()

        self.disco_angle = 0
        self.party_text_drawn = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(16)  # ~60 FPS

    def update_frame(self):
        global phase, running, balls, disco_balls, t, mouse_pos, party_text_drawn
        if not running:
            QApplication.quit()
            return
        self.update()

    def paintEvent(self, event):
        global phase, balls, disco_balls, t, mouse_pos, party_text_drawn
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # Semi-transparent fade trail
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 30))

        if phase == 0:
            self.phase1_paint(painter, w, h, cx, cy)
        elif phase == 1:
            self.phase2_paint(painter, w, h, cx, cy)
        else:
            self.phase3_paint(painter, w, h, cx, cy)

        painter.end()

    def phase1_paint(self, painter, w, h, cx, cy):
        global balls, disco_balls, t

        # Spawn disco balls
        if t % 500 == 0 and len(disco_balls) < 15:
            disco_balls.append({
                'x': random.randint(50, w - 50),
                'y': random.randint(50, h - 50),
                'r': random.randint(30, 80),
            })

        # Draw disco balls
        for ball in disco_balls:
            self.draw_disco_ball(painter, ball['x'], ball['y'], ball['r'], t)

        # Spawn flashing balls
        if t % 100 == 0 and len(balls) < 50:
            r, g, b = hsv_to_rgb(random.random(), 1.0, 1.0)
            balls.append({
                'x': random.randint(0, w),
                'y': random.randint(0, h),
                'r': random.randint(5, 20),
                'color': QColor(r, g, b),
                'life': 120,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3)
            })

        # Update and draw balls
        for ball in balls[:]:
            painter.setBrush(QBrush(ball['color']))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(int(ball['x']), int(ball['y'])), ball['r'], ball['r'])
            ball['x'] += ball['vx']
            ball['y'] += ball['vy']
            ball['vy'] += 0.1
            ball['life'] -= 1
            if ball['life'] <= 0 or ball['x'] < -50 or ball['x'] > self.width() + 50:
                balls.remove(ball)

    def phase2_paint(self, painter, w, h, cx, cy):
        global balls, disco_balls, t, mouse_pos

        # Get mouse position
        try:
            mouse_pos = self.mapFromGlobal(QApplication.primaryScreen().cursor().pos())
        except:
            pass

        # Draw disco balls
        for ball in disco_balls:
            self.draw_disco_ball(painter, ball['x'], ball['y'], ball['r'], t)

        # Draw bouncing balls
        for ball in balls[:]:
            painter.setBrush(QBrush(ball['color']))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(int(ball['x']), int(ball['y'])), ball['r'], ball['r'])
            ball['x'] += ball['vx']
            ball['y'] += ball['vy']
            ball['vy'] += 0.1
            ball['life'] -= 1
            if ball['life'] <= 0:
                balls.remove(ball)

        # Spawn new balls
        if t % 80 == 0 and len(balls) < 80:
            r, g, b = hsv_to_rgb(random.random(), 1.0, 1.0)
            balls.append({
                'x': random.randint(0, w),
                'y': random.randint(0, h),
                'r': random.randint(5, 20),
                'color': QColor(r, g, b),
                'life': 120,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3)
            })

        # Mini disco ball follows mouse
        if mouse_pos:
            mx, my = mouse_pos.x(), mouse_pos.y()
            self.draw_disco_ball(painter, mx, my, 40, t)

        # Rainbow lines from center
        for i in range(16):
            angle = t * 0.01 + i * (2 * math.pi / 16)
            x2 = cx + int(w * 0.6 * math.cos(angle))
            y2 = cy + int(h * 0.6 * math.sin(angle))
            r, g, b = hsv_to_rgb(i / 16 + t * 0.01, 1.0, 1.0)
            painter.setPen(QPen(QColor(r, g, b), 2))
            painter.drawLine(cx, cy, x2, y2)

    def phase3_paint(self, painter, w, h, cx, cy):
        global t, party_text_drawn

        if not self.party_text_drawn:
            self.party_text_drawn = True

        # Draw PARTY MODE text
        text = "PARTY MODE"
        font = QFont("monospace", 48, QFont.Bold)
        painter.setFont(font)
        for i, ch in enumerate(text):
            x = cx - len(text) * 12 + i * 24
            y = cy + int(50 * math.sin(i * 0.2 + t * 0.1))
            r, g, b = hsv_to_rgb(i / len(text) + t * 0.01, 1.0, 1.0)
            painter.setPen(QPen(QColor(r, g, b), 3))
            painter.drawText(x, y, ch)

        # Warp mouse to center
        if t % 60 == 0:
            try:
                QApplication.primaryScreen().cursor().setPos(cx, cy)
            except:
                pass

    def draw_disco_ball(self, painter, x, y, r, t):
        self.disco_angle = getattr(self, 'disco_angle', 0) + 0.05
        for i in range(12):
            angle = self.disco_angle + i * math.pi / 6
            x1 = int(x + math.cos(angle) * r * 0.3)
            y1 = int(y + math.sin(angle) * r * 0.3)
            x2 = int(x + math.cos(angle) * r)
            y2 = int(y + math.sin(angle) * r)
            r, g, b = hsv_to_rgb(i / 12 + t * 0.001, 1.0, 1.0)
            painter.setPen(QPen(QColor(r, g, b), 2))
            painter.drawLine(x1, y1, x2, y2)

    def closeEvent(self, event):
        global running
        running = False
        event.accept()


def run_qt_visualizer():
    app = QApplication.instance() or QApplication(sys.argv)
    visualizer = QtVisualizer()
    visualizer.show()
    app.exec()


# ============================================================
# Xlib Backend (X11 only - fallback)
# ============================================================
def run_xlib_visualizer():
    print("Xlib backend not implemented in this version. Use Qt backend.")
    return


# ============================================================
# Phase Controller
# ============================================================
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


# ============================================================
# Main
# ============================================================
def check_deps():
    missing = []
    if not HAS_QT:
        missing.append("PySide6 (pip install PySide6)")
    if not HAS_PYAUDIO:
        missing.append("pyaudio (pip install pyaudio)")
    if missing:
        print("Missing dependencies:")
        for m in missing:
            print(f"  {m}")
        return False
    return True


def signal_handler(sig, frame):
    global running
    running = False
    sys.exit(0)


def main():
    global phase, t, running

    if not check_deps():
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🎉 PARTY MODE STARTING (Qt backend - works on X11 + Wayland)")
    print("Phase 1 (60s): Balls & Disco - bytebeat 1")
    print("Phase 2 (60s): Balls + Disco + Mouse Disco + Rainbow Lines - bytebeat 2")
    print("Phase 3 (30s): Mouse Control + PARTY MODE text - bytebeat 3")
    print("Press Ctrl+C to stop at any time")
    print()

    audio = AudioThread()
    audio.start()

    controller = PhaseController()
    controller.start()

    # Run Qt visualizer in main thread
    try:
        run_qt_visualizer()
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        audio.stop()
        print("\n🎉 PARTY MODE STOPPED")


if __name__ == "__main__":
    main()
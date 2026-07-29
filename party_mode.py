#!/usr/bin/env python3
"""
Party Mode v3.0 - Enhanced Bytebeat Visualizer for Linux
Features: 6 phases, particle explosions, audio-reactive bars, glitch effects,
3D wireframes, plasma, tunnel effects, mouse control, PARTY MODE text.
Works on X11 + Wayland via Qt (PySide6).
Press Ctrl+C in this terminal to stop at any time.
"""

import sys
import os
import math
import time
import threading
import random
import signal

try:
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtCore import Qt, QTimer, QPoint, QRect
    from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QRadialGradient
    HAS_QT = True
except ImportError:
    HAS_QT = False

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
particles = []
bars = []
wireframe_points = []
plasma_offset = 0


# ============================================================
# BYTBEAT GENERATORS (6 phases)
# ============================================================
def bytebeat1(t):
    """Phase 1: Classic - t*(1+'4451'[t>>13&3]/10)&t>>9+(.003*t&3)"""
    idx = (t >> 13) & 3
    mult = 1 + int('4451'[idx]) / 10
    return int(t * mult) & (t >> 9) + int(.003 * t & 3)


def bytebeat2(t):
    """Phase 2: Balls & disco keep going"""
    arr = [2, 2, 2, 2, 3, 3, 4, 4]
    div = arr[(t >> 14) % 8]
    part1 = int(pow(2.75, -t / 2048 % 8 + 8)) & 128
    part2 = (t * (t & (t >> 11)) & 64)
    part3 = (t // div) & 128
    return (part1 + part2) | part3


def bytebeat3(t):
    """Phase 3: Mouse control + PARTY MODE"""
    shift = t & (t >> 11)
    inner = (t >> 4) >> shift
    sign = -1 if (inner & 128) else 1
    part1 = inner * sign
    div = 2 if (t & 65535) else 3
    part2 = (t >> (t // div)) & 63
    part3 = int(30000 / (t & 4095)) & 100
    return (part1 + part2 + part3) & 255


def bytebeat4(t):
    """Phase 4: Glitch - audio-reactive bars"""
    return (t * (t >> 8) | t >> 9) & 46 & t >> 8 ^ (t & t >> 13 | t >> 6)


def bytebeat5(t):
    """Phase 5: 3D Wireframe - complex harmonics"""
    return (t * (t >> 12) & 63) | (t * (t >> 9) & 31) | ((t >> 7) & 15) * (t & 127)


def bytebeat6(t):
    """Phase 6: Final - takes mouse control, draws PARTY MODE, ends"""
    return (((t >> 4) >> (t & (t >> 11))) * (((t >> 4) >> (t & (t >> 11))) & 128 and -1 or 1)) + (t >> t / (t & 65536 and 2 or 3) & 63) + (30000 / (t & 4095) & 100)


BYTEBEATS = [bytebeat1, bytebeat2, bytebeat3, bytebeat4, bytebeat5, bytebeat6]
PHASE_NAMES = [
    "Balls & Disco",
    "Balls + Mouse Disco + Rainbow Lines",
    "Mouse Control + PARTY MODE",
    "Glitch + Audio-Reactive Bars",
    "3D Wireframe + Plasma",
    "Final: Mouse Control + PARTY MODE"
]
PHASE_DURATIONS = [45, 45, 30, 45, 45, 30]  # seconds


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


def rgb_to_qcolor(r, g, b):
    return QColor(r, g, b)


# ============================================================
# AUDIO THREAD
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
                if phase < len(BYTEBEATS):
                    val = int(BYTEBEATS[phase](t)) & 255
                else:
                    val = 0
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
# PARTICLE SYSTEM
# ============================================================
class Particle:
    def __init__(self, x, y, color=None, life=60):
        self.x = x
        self.y = y
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-5, 5)
        self.r = random.randint(2, 8)
        self.life = life
        self.color = color or QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.gravity = random.uniform(-0.1, 0.1)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1

    def draw(self, painter):
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(int(self.x), int(self.y)), self.r, self.r)


def spawn_explosion(x, y, count=20):
    for _ in range(count):
        particles.append(Particle(x, y, life=random.randint(30, 120)))


# ============================================================
# VISUALIZER WIDGET
# ============================================================
class PartyVisualizer(QWidget):
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
        self.wireframe_points = []
        self.plasma_offset = 0
        self.glitch_offset = 0

        # Initialize wireframe points for 3D effect
        for i in range(50):
            angle = i * (2 * math.pi / 50)
            self.wireframe_points.append({
                'angle': angle,
                'radius': random.randint(100, 400),
                'z': random.uniform(0, 100),
                'speed': random.uniform(0.01, 0.05)
            })

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(16)  # ~60 FPS

    def update_frame(self):
        global running
        if not running:
            QApplication.quit()
            return
        self.update()

    def paintEvent(self, event):
        global phase, t, mouse_pos, party_text_drawn, particles, balls, disco_balls
        global plasma_offset, glitch_offset

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # Semi-transparent fade trail for smooth animation
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 20))

        # Update mouse position
        try:
            mouse_pos = QApplication.primaryScreen().cursor().pos()
        except:
            pass

        # Draw based on phase
        if phase == 0:
            self.phase1_paint(painter, w, h, cx, cy)
        elif phase == 1:
            self.phase2_paint(painter, w, h, cx, cy)
        elif phase == 2:
            self.phase3_paint(painter, w, h, cx, cy)
        elif phase == 3:
            self.phase4_paint(painter, w, h, cx, cy)
        elif phase == 4:
            self.phase5_paint(painter, w, h, cx, cy)
        elif phase == 5:
            self.phase6_paint(painter, w, h, cx, cy)

        # Update animations
        self.disco_angle += 0.05
        self.plasma_offset += 0.02
        self.glitch_offset += 1

        # Update and draw particles
        for p in particles[:]:
            p.update()
            if p.life <= 0:
                particles.remove(p)
            else:
                p.draw(painter)

        painter.end()

    def phase1_paint(self, painter, w, h, cx, cy):
        """Phase 1: Balls & Disco"""
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
            if ball['life'] <= 0 or ball['x'] < -50 or ball['x'] > w + 50:
                balls.remove(ball)

        # Spawn explosion particles occasionally
        if t % 200 == 0:
            spawn_explosion(random.randint(0, w), random.randint(0, h), count=10)

    def phase2_paint(self, painter, w, h, cx, cy):
        """Phase 2: Balls + Disco + Mouse Disco + Rainbow Lines"""
        global balls, disco_balls, t, mouse_pos

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

        # Spawn explosion particles
        if t % 150 == 0:
            spawn_explosion(random.randint(0, w), random.randint(0, h), count=15)

    def phase3_paint(self, painter, w, h, cx, cy):
        """Phase 3: Mouse Control + PARTY MODE text"""
        global t, party_text_drawn

        if not self.party_text_drawn:
            self.party_text_drawn = True

        # Draw PARTY MODE text with rainbow colors
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

        # Draw particles around text
        if t % 30 == 0:
            for _ in range(5):
                px = cx + random.randint(-200, 200)
                py = cy + random.randint(-50, 50)
                spawn_explosion(px, py, count=3)

    def phase4_paint(self, painter, w, h, cx, cy):
        """Phase 4: Glitch + Audio-Reactive Bars"""
        global t, glitch_offset

        # Audio-reactive bars from bottom
        num_bars = 64
        for i in range(num_bars):
            # Use bytebeat value for bar height
            val = int(bytebeat4(t + i * 100)) & 255
            bar_h = int(val * h / 256 * 0.5)
            x = i * (w // num_bars)
            y = h - bar_h
            r, g, b = hsv_to_rgb(i / num_bars + t * 0.01, 1.0, 1.0)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(r, g, b)))
            painter.drawRect(x, y, w // num_bars - 2, bar_h)

        # Glitch effect - random rectangles
        if t % 10 == 0:
            for _ in range(5):
                gx = random.randint(0, w - 100)
                gy = random.randint(0, h - 50)
                gw = random.randint(50, 200)
                gh = random.randint(10, 50)
                r, g, b = hsv_to_rgb(random.random(), 1.0, 1.0)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(r, g, b)))
                painter.drawRect(gx, gy, gw, gh)

        # Glitch lines
        if t % 5 == 0:
            for _ in range(3):
                y = random.randint(0, h)
                r, g, b = hsv_to_rgb(random.random(), 1.0, 1.0)
                painter.setPen(QPen(QColor(r, g, b), 1))
                painter.drawLine(0, y, w, y)

    def phase5_paint(self, painter, w, h, cx, cy):
        """Phase 5: 3D Wireframe + Plasma"""
        global t, plasma_offset

        # 3D Wireframe rotating cube
        points = []
        for p in self.wireframe_points:
            p['angle'] += p['speed']
            p['z'] = (p['z'] + 1) % 100
            x3d = p['radius'] * math.cos(p['angle']) * (p['z'] / 100)
            y3d = p['radius'] * math.sin(p['angle']) * (p['z'] / 100)
            x2d = cx + x3d
            y2d = cy + y3d
            points.append((x2d, y2d))

        # Draw wireframe lines
        for i in range(len(points)):
            j = (i + 1) % len(points)
            r, g, b = hsv_to_rgb(i / len(points) + t * 0.005, 1.0, 1.0)
            painter.setPen(QPen(QColor(r, g, b), 1))
            painter.drawLine(int(points[i][0]), int(points[i][1]),
                           int(points[j][0]), int(points[j][1]))

        # Plasma effect - concentric circles
        for i in range(20):
            radius = 50 + i * 30 + int(20 * math.sin(t * 0.02 + i))
            r, g, b = hsv_to_rgb(i / 20 + t * 0.01, 0.8, 0.8)
            painter.setPen(QPen(QColor(r, g, b), 2))
            painter.drawEllipse(QPoint(cx, cy), radius, radius)

        # Spawn particles
        if t % 100 == 0:
            spawn_explosion(cx + random.randint(-300, 300), cy + random.randint(-300, 300), count=20)

    def phase6_paint(self, painter, w, h, cx, cy):
        """Phase 6: Final - Mouse Control + PARTY MODE + Everything"""
        global t, party_text_drawn

        # Draw everything from all phases
        self.phase2_paint(painter, w, h, cx, cy)
        self.phase4_paint(painter, w, h, cx, cy)
        self.phase5_paint(painter, w, h, cx, cy)

        # Draw PARTY MODE text with glitch effect
        text = "PARTY MODE"
        font = QFont("monospace", 64, QFont.Bold)
        painter.setFont(font)
        for i, ch in enumerate(text):
            x = cx - len(text) * 16 + i * 32 + int(random.randint(-5, 5))
            y = cy + 100 + int(random.randint(-5, 5))
            r, g, b = hsv_to_rgb(i / len(text) + t * 0.01, 1.0, 1.0)
            painter.setPen(QPen(QColor(r, g, b), 4))
            painter.drawText(x, y, ch)

        # Warp mouse to center
        if t % 30 == 0:
            try:
                QApplication.primaryScreen().cursor().setPos(cx, cy)
            except:
                pass

        # Spawn lots of particles
        if t % 20 == 0:
            spawn_explosion(cx + random.randint(-400, 400), cy + random.randint(-200, 200), count=30)

    def draw_disco_ball(self, painter, x, y, r, t):
        self.disco_angle += 0.05
        for i in range(12):
            angle = self.disco_angle + i * math.pi / 6
            x1 = int(x + math.cos(angle) * r * 0.3)
            y1 = int(y + math.sin(angle) * r * 0.3)
            x2 = int(x + math.cos(angle) * r)
            y2 = int(y + math.sin(angle) * r)
            r_val, g_val, b_val = hsv_to_rgb(i / 12 + t * 0.001, 1.0, 1.0)
            painter.setPen(QPen(QColor(r_val, g_val, b_val), 2))
            painter.drawLine(x1, y1, x2, y2)

    def closeEvent(self, event):
        global running
        running = False
        event.accept()


# ============================================================
# PHASE CONTROLLER
# ============================================================
class PhaseController(threading.Thread):
    def run(self):
        global phase, running, party_text_drawn
        for i, duration in enumerate(PHASE_DURATIONS):
            if not running:
                return
            print(f"\n>>> PHASE {i+1}: {PHASE_NAMES[i]} ({duration}s)")
            time.sleep(duration)
            if running:
                phase = i + 1
                if i + 1 >= len(PHASE_DURATIONS):
                    running = False
                    print("\n>>> PARTY OVER!")


# ============================================================
# MAIN
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

    print("🎉 PARTY MODE v3.0 - ENHANCED")
    print("=" * 50)
    for i, name in enumerate(PHASE_NAMES):
        print(f"Phase {i+1} ({PHASE_DURATIONS[i]}s): {name}")
    print("=" * 50)
    print("Effects: Balls, Disco Balls, Rainbow Lines, Particle Explosions,")
    print("         Glitch, Audio-Reactive Bars, 3D Wireframe, Plasma, Mouse Control")
    print("Press Ctrl+C to stop at any time")
    print()

    audio = AudioThread()
    audio.start()

    controller = PhaseController()
    controller.start()

    try:
        app = QApplication.instance() or QApplication(sys.argv)
        visualizer = PartyVisualizer()
        visualizer.show()
        app.exec()
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        audio.stop()
        print("\n🎉 PARTY MODE STOPPED")


if __name__ == "__main__":
    main()
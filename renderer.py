from PyQt5.QtWidgets import QOpenGLWidget, QToolButton, QLabel
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush, QRadialGradient,
                          QPainterPath, QPolygonF, QLinearGradient)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
import math
import time


class Renderer(QOpenGLWidget):
    cell_selected = pyqtSignal(object)

    def __init__(self, environment, parent=None):
        super().__init__(parent)
        self.environment = environment
        self.selected_cell = None
        self.draw_food_mode = False
        self.erase_food_mode = False
        self.move_light_mode = False

        # View transform
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self._last_mouse = None
        self._panning = False

        # Animation time
        self._anim_time = 0.0
        self._last_frame_time = time.monotonic()

        # Compatibility shim: cell_items maps id -> True
        self.cell_items = {}

        # Tool buttons (kept for main_window layout compatibility)
        self.draw_food_button = QToolButton()
        self.draw_food_button.setText("Draw Food")
        self.draw_food_button.setCheckable(True)
        self.draw_food_button.clicked.connect(self.toggle_draw_food_mode)

        self.erase_food_button = QToolButton()
        self.erase_food_button.setText("Erase Food")
        self.erase_food_button.setCheckable(True)
        self.erase_food_button.clicked.connect(self.toggle_erase_food_mode)

        self.energy_label = QLabel()

        self.setMinimumSize(500, 500)
        self.setMouseTracking(True)

    # ------------------------------------------------------------------ helpers
    def _screen_to_world(self, sx, sy):
        cx, cy = self.width() / 2, self.height() / 2
        ex, ey = self.environment.center
        wx = (sx - cx - self._pan_offset.x()) / self._zoom + ex
        wy = (sy - cy - self._pan_offset.y()) / self._zoom + ey
        return wx, wy

    def _apply_transform(self, painter):
        cx, cy = self.width() / 2, self.height() / 2
        ex, ey = self.environment.center
        painter.translate(cx + self._pan_offset.x(), cy + self._pan_offset.y())
        painter.scale(self._zoom, self._zoom)
        painter.translate(-ex, -ey)

    # ------------------------------------------------------------------ paint
    def paintGL(self):
        now = time.monotonic()
        self._anim_time += now - self._last_frame_time
        self._last_frame_time = now
        t = self._anim_time

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Deep-space background
        painter.fillRect(self.rect(), QColor(12, 14, 18))

        painter.save()
        self._apply_transform(painter)

        self._draw_petri_dish(painter, t)
        self._draw_food_batch(painter, t)
        self._draw_cells(painter, t)
        self._draw_light_source(painter, t)

        painter.restore()

        # HUD overlay
        if self.selected_cell:
            self.energy_label.setText(f"Energy: {self.selected_cell.energy:.1f}")

        painter.end()

    # -------------------------------------------------------- petri dish
    def _draw_petri_dish(self, painter, t):
        env = self.environment
        r = env.radius
        cx, cy = env.center
        lx, ly = env.light_source
        intensity = getattr(env, 'light_intensity', 1.0)
        light_color = getattr(env, 'light_color', (255, 255, 200))

        # Agar-gel base
        base_grad = QRadialGradient(cx, cy, r)
        base_grad.setColorAt(0.0, QColor(22, 42, 28))
        base_grad.setColorAt(1.0, QColor(10, 20, 14))
        painter.setBrush(QBrush(base_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Light spread across agar
        spread_r = r * 0.85
        light_alpha = int(70 * intensity)
        lc = QColor(*light_color, light_alpha)
        lc_fade = QColor(*light_color, 0)
        light_grad = QRadialGradient(lx, ly, spread_r)
        light_grad.setColorAt(0.0, lc)
        light_grad.setColorAt(0.45, QColor(*light_color, int(25 * intensity)))
        light_grad.setColorAt(1.0, lc_fade)
        painter.setBrush(QBrush(light_grad))
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Dish rim (glass look)
        rim_grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        rim_grad.setColorAt(0.0, QColor(200, 210, 220, 160))
        rim_grad.setColorAt(0.5, QColor(120, 140, 160, 80))
        rim_grad.setColorAt(1.0, QColor(180, 190, 200, 140))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QBrush(rim_grad), 4))
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Inner reflection arc
        painter.setPen(QPen(QColor(255, 255, 255, 30), 2))
        painter.drawArc(QRectF(cx - r + 10, cy - r + 10, r * 2 - 20, r * 2 - 20),
                        30 * 16, 80 * 16)

    # -------------------------------------------------------- food
    def _draw_food_batch(self, painter, t):
        if not self.environment.food:
            return

        # Batch all food into one path
        path = QPainterPath()
        glow_path = QPainterPath()
        for fx, fy in self.environment.food:
            # Tiny pulsing food particles
            pulse = 0.8 + 0.2 * math.sin(t * 2.5 + fx * 0.1 + fy * 0.07)
            s = 2.0 * pulse
            path.addEllipse(QRectF(fx - s, fy - s, s * 2, s * 2))
            glow_path.addEllipse(QRectF(fx - s * 2, fy - s * 2, s * 4, s * 4))

        # Glow layer
        painter.setBrush(QColor(60, 230, 100, 25))
        painter.setPen(Qt.NoPen)
        painter.drawPath(glow_path)

        # Core food dots
        painter.setBrush(QColor(70, 240, 110, 220))
        painter.drawPath(path)

    # -------------------------------------------------------- cells
    def _draw_cells(self, painter, t):
        env = self.environment
        lx, ly = env.light_source
        radius = env.radius
        intensity = getattr(env, 'light_intensity', 1.0)

        for cell in env.cells:
            px, py = float(cell.position[0]), float(cell.position[1])
            size = max(float(cell.genome.genes['size']), 6.0)
            pulse_phase = getattr(cell, 'pulse_phase', 0.0)

            # Organic pulsing — larger cells pulse slower
            pulse_rate = 1.8 / max(size / 10, 0.5)
            pulse = 1.0 + 0.06 * math.sin(t * pulse_rate + pulse_phase)
            draw_size = size * pulse

            r_f, g_f, b_f = cell.genome.genes['color']
            base_color = QColor.fromRgbF(
                min(1, r_f), min(1, g_f), min(1, b_f))

            # --- Photocyte: light-reactive glow ---
            if cell.type == "Photocyte":
                dist_to_light = math.hypot(px - lx, py - ly)
                light_factor = max(0.0, 1.0 - dist_to_light / radius) * intensity
                glow_brightness = getattr(cell, 'glow_intensity', light_factor)
                if glow_brightness > 0.05:
                    glow_r = draw_size * (1.5 + glow_brightness)
                    outer_glow = QColor(80, 255, 120, int(90 * glow_brightness))
                    grad = QRadialGradient(px, py, glow_r)
                    grad.setColorAt(0.0, QColor(160, 255, 160, int(120 * glow_brightness)))
                    grad.setColorAt(0.6, outer_glow)
                    grad.setColorAt(1.0, QColor(0, 200, 80, 0))
                    painter.setBrush(QBrush(grad))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(QRectF(px - glow_r, py - glow_r,
                                               glow_r * 2, glow_r * 2))

            # --- Phagocyte: danger aura ---
            if cell.type == "Phagocyte":
                aura_pulse = 0.5 + 0.5 * abs(math.sin(t * 1.2 + pulse_phase))
                aura_r = draw_size * 1.4
                painter.setBrush(QColor(220, 80, 30, int(40 * aura_pulse)))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QRectF(px - aura_r, py - aura_r,
                                           aura_r * 2, aura_r * 2))

            # --- Adhesin ring ---
            if cell.adhesin:
                adhesin_r = draw_size * 1.2 + 8
                adhesin_col = QColor(base_color)
                adhesin_col.setAlpha(35)
                painter.setBrush(adhesin_col)
                painter.setPen(QPen(QColor(base_color.red(),
                                           base_color.green(),
                                           base_color.blue(), 60), 1.5,
                                    Qt.DotLine))
                painter.drawEllipse(QRectF(px - adhesin_r, py - adhesin_r,
                                           adhesin_r * 2, adhesin_r * 2))

            # --- Flagellum / tail (animated wave) ---
            if cell.genome.genes['has_tail']:
                self._draw_flagellum(painter, cell, px, py, draw_size,
                                     base_color, t)

            # --- Cell body gradient ---
            highlight = QColor(base_color).lighter(180)
            highlight.setAlpha(220)
            shadow = QColor(base_color).darker(170)
            body_grad = QRadialGradient(
                px - draw_size * 0.25, py - draw_size * 0.25, draw_size * 0.9)
            body_grad.setColorAt(0.0, highlight)
            body_grad.setColorAt(0.4, base_color)
            body_grad.setColorAt(1.0, shadow)
            painter.setBrush(QBrush(body_grad))

            # Outline per type
            if cell is self.selected_cell:
                pen = QPen(QColor(255, 60, 60), 2.5, Qt.DashLine)
            elif cell.type == "Phagocyte":
                pen = QPen(QColor(230, 110, 40), 1.8)
            elif cell.type == "Bacteria":
                pen = QPen(QColor(100, 210, 160), 0.8)
            elif cell.type == "Photocyte":
                pen = QPen(QColor(60, 250, 100), 1.2)
            else:
                pen = QPen(QColor(90, 100, 95), 0.8)
            painter.setPen(pen)
            painter.drawEllipse(QRectF(px - draw_size / 2,
                                       py - draw_size / 2,
                                       draw_size, draw_size))

            # --- Nucleus (non-bacteria) ---
            if cell.type != "Bacteria":
                ns = draw_size * 0.28
                nuc_col = QColor(base_color).darker(200)
                nuc_col.setAlpha(170)
                # Nucleus wanders slightly
                nx = px + math.sin(t * 0.7 + pulse_phase) * draw_size * 0.08
                ny = py + math.cos(t * 0.5 + pulse_phase) * draw_size * 0.08
                painter.setBrush(nuc_col)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QRectF(nx - ns / 2, ny - ns / 2, ns, ns))
                # Nucleolus
                nn = ns * 0.4
                painter.setBrush(QColor(base_color).lighter(140))
                painter.drawEllipse(QRectF(nx - nn / 2, ny - nn / 2, nn, nn))

            # --- Membrane shimmer (specular highlight) ---
            shimmer_alpha = int(60 + 40 * math.sin(t * 4 + pulse_phase))
            painter.setBrush(QColor(255, 255, 255, shimmer_alpha))
            painter.setPen(Qt.NoPen)
            sh = draw_size * 0.22
            painter.drawEllipse(QRectF(
                px - draw_size * 0.28, py - draw_size * 0.32, sh, sh * 0.6))

    def _draw_flagellum(self, painter, cell, px, py, draw_size, base_color, t):
        """Render a wavy, multi-segment flagellum."""
        angle = cell.angle
        pulse_phase = getattr(cell, 'pulse_phase', 0.0)
        tail_len = draw_size * 2.2
        segments = 10
        seg_len = tail_len / segments

        # Attach point at back of cell
        attach_angle = angle + math.pi
        ax = px + math.cos(attach_angle) * draw_size * 0.4
        ay = py + math.sin(attach_angle) * draw_size * 0.4

        path = QPainterPath()
        path.moveTo(ax, ay)

        cx_prev, cy_prev = ax, ay
        for i in range(1, segments + 1):
            # Wave: amplitude grows toward the tip
            wave = math.sin(t * 9 + pulse_phase + i * 0.7) * (draw_size * 0.08 * i / segments)
            perp_x = -math.sin(attach_angle)
            perp_y = math.cos(attach_angle)
            cx_n = cx_prev + math.cos(attach_angle) * seg_len + perp_x * wave
            cy_n = cy_prev + math.sin(attach_angle) * seg_len + perp_y * wave
            path.lineTo(cx_n, cy_n)
            cx_prev, cy_prev = cx_n, cy_n

        alpha = 180
        tail_color = QColor(base_color.red(), base_color.green(), base_color.blue(), alpha)
        pen = QPen(tail_color, max(1.5, draw_size * 0.12), Qt.SolidLine,
                   Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    # -------------------------------------------------------- light source
    def _draw_light_source(self, painter, t):
        lx, ly = self.environment.light_source
        intensity = getattr(self.environment, 'light_intensity', 1.0)
        light_color = getattr(self.environment, 'light_color', (255, 255, 200))

        lc = QColor(*light_color)

        # Pulsing outer corona
        corona_r = 18 + 5 * math.sin(t * 2.5)
        corona_grad = QRadialGradient(lx, ly, corona_r)
        corona_grad.setColorAt(0.0, QColor(lc.red(), lc.green(), lc.blue(),
                                           int(120 * intensity)))
        corona_grad.setColorAt(1.0, QColor(lc.red(), lc.green(), lc.blue(), 0))
        painter.setBrush(QBrush(corona_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(lx - corona_r, ly - corona_r,
                                   corona_r * 2, corona_r * 2))

        # Rays (rotating)
        ray_color = QColor(lc.red(), lc.green(), lc.blue(), int(140 * intensity))
        painter.setPen(QPen(ray_color, 1.2))
        num_rays = 8
        for i in range(num_rays):
            ray_angle = i * (math.pi * 2 / num_rays) + t * 0.6
            inner = 6.0
            outer = 13.0 + 3 * math.sin(t * 3 + i)
            painter.drawLine(
                QPointF(lx + math.cos(ray_angle) * inner,
                        ly + math.sin(ray_angle) * inner),
                QPointF(lx + math.cos(ray_angle) * outer,
                        ly + math.sin(ray_angle) * outer))

        # Core bright spot
        core_r = 5.0 + 1.5 * math.sin(t * 4)
        core_grad = QRadialGradient(lx - 1.5, ly - 1.5, core_r)
        core_grad.setColorAt(0.0, Qt.white)
        core_grad.setColorAt(0.5, lc)
        core_grad.setColorAt(1.0, QColor(lc.red(), lc.green(), lc.blue(), 0))
        painter.setBrush(QBrush(core_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(lx - core_r, ly - core_r,
                                   core_r * 2, core_r * 2))

    # ---------------------------------------------------------------- public API
    def update_scene(self):
        self.cell_items = {cell.id: True for cell in self.environment.cells}
        self.update()

    # ---------------------------------------------------------------- mouse / input
    def mousePressEvent(self, event):
        wx, wy = self._screen_to_world(event.x(), event.y())

        # Light dragging
        if self.move_light_mode and event.button() == Qt.LeftButton:
            ex, ey = self.environment.center
            r = self.environment.radius
            if math.hypot(wx - ex, wy - ey) <= r:
                self.environment.light_source = (wx, wy)
                self.update()
            return

        # Pan with right button or middle
        if event.button() in (Qt.RightButton, Qt.MiddleButton):
            self._panning = True
            self._last_mouse = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        if event.button() == Qt.LeftButton:
            if self.draw_food_mode:
                self.environment.food.append((wx, wy))
                self.update_scene()
                return
            if self.erase_food_mode:
                for food in self.environment.food[:]:
                    if math.hypot(wx - food[0], wy - food[1]) < 6:
                        self.environment.food.remove(food)
                        self.update_scene()
                        break
                return

            # Cell selection — pick nearest within radius
            best, best_dist = None, float('inf')
            for cell in self.environment.cells:
                dist = math.hypot(wx - cell.position[0], wy - cell.position[1])
                cell_r = max(cell.genome.genes['size'] / 2, 6)
                if dist < cell_r and dist < best_dist:
                    best_dist = dist
                    best = cell
            self.selected_cell = best
            self.cell_selected.emit(best)
            self.update()

    def mouseMoveEvent(self, event):
        if self._panning and self._last_mouse is not None:
            delta = event.pos() - self._last_mouse
            self._pan_offset += QPointF(delta.x(), delta.y())
            self._last_mouse = event.pos()
            self.update()
            return

        if self.move_light_mode and event.buttons() & Qt.LeftButton:
            wx, wy = self._screen_to_world(event.x(), event.y())
            ex, ey = self.environment.center
            r = self.environment.radius
            if math.hypot(wx - ex, wy - ey) <= r:
                self.environment.light_source = (wx, wy)
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.RightButton, Qt.MiddleButton):
            self._panning = False
            self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom = max(0.15, min(12.0, self._zoom * factor))
        self.update()

    def toggle_draw_food_mode(self):
        self.draw_food_mode = self.draw_food_button.isChecked()
        if self.draw_food_mode:
            self.erase_food_button.setChecked(False)
            self.erase_food_mode = False

    def toggle_erase_food_mode(self):
        self.erase_food_mode = self.erase_food_button.isChecked()
        if self.erase_food_mode:
            self.draw_food_button.setChecked(False)
            self.draw_food_mode = False

    def zoom_in(self):
        self._zoom = min(12.0, self._zoom * 1.2)
        self.update()

    def zoom_out(self):
        self._zoom = max(0.15, self._zoom / 1.2)
        self.update()

    def scroll(self, dx, dy):
        self._pan_offset += QPointF(dx, dy)
        self.update()

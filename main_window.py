from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QCheckBox, QSlider,
                             QGroupBox, QComboBox, QScrollArea, QDoubleSpinBox,
                             QFileDialog, QSizePolicy)
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter
import random
import math

from renderer import Renderer
from simulation import SimulationEngine
from environment import Environment
from cell import Cell, Genome, Bacteria, Phagocyte, Photocyte
from file_io import save_genome, load_genome


BIT_TO_BASE = {0: 'C', 1: 'G', 2: 'A', 3: 'T'}
BASE_COLORS = {
    'C': QColor(80, 140, 255),
    'G': QColor(60, 200, 120),
    'A': QColor(255, 90, 90),
    'T': QColor(255, 200, 80),
}

def dna_to_bases(dna, bits=128):
    return [BIT_TO_BASE[(dna >> i) & 3] for i in range(0, bits, 2)]


class DNADock(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMouseTracking(True)

        self.bases = []
        self.hover_index = None
        self._min_base_size = 14
        self.focus_scale = 3.2

    def _compute_metrics(self):
        n = len(self.bases)
        w = self.width()
        base_size = (w - n * 6) / n
        base_size = max(self._min_base_size, base_size)
        spacing = base_size + 6
        return base_size, spacing

    def _total_width(self):
        _, spacing = self._compute_metrics()
        return len(self.bases) * spacing

    def set_dna(self, dna):
        if dna is None:
            self.bases = []
        else:
            self.bases = dna_to_bases(dna, bits=128)
        self.update()

    def leaveEvent(self, e):
        self.hover_index = None
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def mouseMoveEvent(self, e):
        if not self.bases:
            return
        w = self.width()
        base_size, spacing = self._compute_metrics()
        total = self._total_width()
        start_x = (w - total) / 2
        idx = int((e.x() - start_x) / spacing)
        self.hover_index = idx if 0 <= idx < len(self.bases) else None
        self.update()

    def paintEvent(self, e):
        if not self.bases:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        base_size, spacing = self._compute_metrics()
        total = self._total_width()
        start_x = (w - total) / 2
        center_y = h / 2

        for i, base in enumerate(self.bases):
            scale = self.focus_scale if i == self.hover_index else 1.0
            size = base_size * scale
            x = start_x + i * spacing
            y = center_y
            rect = QRectF(x - (size - base_size) / 2, y - size / 2, size, size)
            p.setBrush(BASE_COLORS[base])
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(rect, 4, 4)
            p.setPen(Qt.white)
            font = p.font()
            font.setBold(True)
            font.setPointSizeF(8 * scale)
            p.setFont(font)
            p.drawText(rect, Qt.AlignCenter, base)


GENE_FIELDS = [
    ('division_threshold', 0,  8, 10.0, 'Division Threshold', 0, 25.5, 0.1),
    ('energy_efficiency',  8,  8, 10.0, 'Energy Efficiency',  0, 25.5, 0.1),
    ('speed',              16, 8, 10.0, 'Speed',              0, 25.5, 0.1),
    ('size',               24, 8, 10.0, 'Size',               0, 25.5, 0.1),
    ('consumption_size_ratio', 32, 8, 10.0, 'Consumption Ratio', 0, 25.5, 0.1),
    ('motility_mode',      40, 2, 1.0,   'Motility',          0, 2,    1),
    ('body_shape',         44, 1, 1.0,   'Oval Shape',        0, 1,    1),
    ('can_consume',        45, 1, 1.0,   'Can Consume',       0, 1,    1),
    ('adhesin',            46, 1, 1.0,   'Adhesin',           0, 1,    1),
    ('nitrogen_reserve',   47, 8, 10.0,  'Nitrogen Reserve',  0, 25.5, 0.1),
    ('radiation_sensitivity', 55, 8, 100.0, 'Radiation Sensitivity', 0, 2.55, 0.01),
    ('color_r',            63, 8, 255.0, 'Colour Red',        0, 1.0,  0.01),
    ('color_g',            71, 8, 255.0, 'Colour Green',      0, 1.0,  0.01),
    ('color_b',            79, 8, 255.0, 'Colour Blue',       0, 1.0,  0.01),
]

class GeneRow(QWidget):
    changed = pyqtSignal()

    def __init__(self, label, minv, maxv, step, is_bool=False, is_combobox=False):
        super().__init__()
        l = QHBoxLayout(self)
        l.setSpacing(6)
        name = QLabel(label)
        name.setMinimumWidth(110)
        l.addWidget(name)

        if is_combobox:
            self.combo = QComboBox()
            self.combo.addItems(["None", "Flagellum", "Cilia"])
            self.combo.currentIndexChanged.connect(self.changed.emit)
            l.addWidget(self.combo)
            l.addStretch()
        elif is_bool:
            self.chk = QCheckBox()
            self.chk.stateChanged.connect(self.changed.emit)
            l.addWidget(self.chk)
            l.addStretch()
        else:
            self.slider = QSlider(Qt.Horizontal)
            self.slider.setRange(int(minv*100), int(maxv*100))
            self.spin = QDoubleSpinBox()
            self.spin.setRange(minv, maxv)
            self.spin.setSingleStep(step)
            self.slider.valueChanged.connect(lambda v: self.spin.setValue(v/100))
            self.spin.valueChanged.connect(lambda v: self.slider.setValue(int(v*100)))
            self.spin.valueChanged.connect(self.changed.emit)
            l.addWidget(self.slider)
            l.addWidget(self.spin)

    def get(self):
        if hasattr(self, 'combo'):
            return self.combo.currentIndex()
        elif hasattr(self, 'chk'):
            return self.chk.isChecked()
        return self.spin.value()

    def set(self, v):
        if hasattr(self, 'combo'):
            self.combo.setCurrentIndex(int(v))
        elif hasattr(self, 'chk'):
            self.chk.setChecked(bool(v))
        else:
            self.spin.setValue(float(v))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Splitsville")
        self.setGeometry(100, 100, 1280, 720)

        root = QWidget()
        self.setCentralWidget(root)
        self.root_layout = QVBoxLayout(root)

        content_layout = QHBoxLayout()
        self.root_layout.addLayout(content_layout, 1)

        sim_layout = QVBoxLayout()
        content_layout.addLayout(sim_layout, 3)

        self.environment = Environment(250)
        self._randomise_light_source()

        self.renderer = Renderer(self.environment)
        self.renderer.cell_selected.connect(self.on_cell_selected)
        sim_layout.addWidget(self.renderer, 1)

        ctrl_row = QHBoxLayout()
        sim_layout.addLayout(ctrl_row)

        self.cell_count_label = QLabel("Cells: 0")
        font = QFont()
        font.setBold(True)
        self.cell_count_label.setFont(font)
        ctrl_row.addWidget(self.cell_count_label)

        ctrl_row.addWidget(self.renderer.draw_food_button)
        ctrl_row.addWidget(self.renderer.erase_food_button)

        self.generate_food_checkbox = QCheckBox("Generate Food")
        self.generate_food_checkbox.setChecked(True)
        ctrl_row.addWidget(self.generate_food_checkbox)

        ctrl_row.addStretch()

        self.zoom_in_button = QPushButton("＋ Zoom")
        self.zoom_in_button.clicked.connect(self.renderer.zoom_in)
        ctrl_row.addWidget(self.zoom_in_button)

        self.zoom_out_button = QPushButton("－ Zoom")
        self.zoom_out_button.clicked.connect(self.renderer.zoom_out)
        ctrl_row.addWidget(self.zoom_out_button)

        sim_ctrl = QHBoxLayout()
        sim_layout.addLayout(sim_ctrl)

        self.start_button = QPushButton("▶ Start")
        self.start_button.setStyleSheet("background-color: #2d7a2d; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px;")
        self.start_button.clicked.connect(self.toggle_simulation)
        sim_ctrl.addWidget(self.start_button)

        self.add_cell_button = QPushButton("+ Cell")
        self.add_cell_button.clicked.connect(lambda: self.add_random_cell("cell"))
        sim_ctrl.addWidget(self.add_cell_button)

        self.add_bacteria_button = QPushButton("+ Bacteria")
        self.add_bacteria_button.clicked.connect(lambda: self.add_random_cell("bacteria"))
        sim_ctrl.addWidget(self.add_bacteria_button)

        self.add_photocyte_button = QPushButton("+ Photocyte")
        self.add_photocyte_button.clicked.connect(lambda: self.add_random_cell("photocyte"))
        sim_ctrl.addWidget(self.add_photocyte_button)

        self.add_phagocyte_button = QPushButton("+ Phagocyte")
        self.add_phagocyte_button.clicked.connect(lambda: self.add_random_cell("phagocyte"))
        sim_ctrl.addWidget(self.add_phagocyte_button)

        self.delete_cell_button = QPushButton("Delete")
        self.delete_cell_button.clicked.connect(self.delete_selected_cell)
        sim_ctrl.addWidget(self.delete_cell_button)

        self.random_button = QPushButton("Random")
        self.random_button.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px;")
        self.random_button.clicked.connect(self.populate_random)
        sim_ctrl.addWidget(self.random_button)

        right_layout = QVBoxLayout()
        content_layout.addLayout(right_layout, 1)

        self.info_label = QLabel("No cell selected")
        self.default_info_font = self.info_label.font()
        right_layout.addWidget(self.info_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.gene_editor_container = QWidget()
        self.gene_editor_layout = QVBoxLayout(self.gene_editor_container)
        self.gene_editor_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area.setWidget(self.gene_editor_container)
        self.gene_editor_container.setVisible(False)
        right_layout.addWidget(self.scroll_area, 1)

        light_group = QGroupBox("☀ Light Source")
        light_group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #555;"
            " border-radius:4px; margin-top:6px; padding-top:10px;}"
            "QGroupBox::title { subcontrol-origin: margin; left:8px; }")
        light_v = QVBoxLayout(light_group)

        self.light_enabled_checkbox = QCheckBox("Light Enabled")
        self.light_enabled_checkbox.setChecked(True)
        self.light_enabled_checkbox.toggled.connect(self.toggle_light_enabled)
        light_v.addWidget(self.light_enabled_checkbox)

        self.move_light_checkbox = QCheckBox("Move Light (drag)")
        self.move_light_checkbox.toggled.connect(self._toggle_move_light)
        light_v.addWidget(self.move_light_checkbox)

        centre_btn = QPushButton("⊙ Centre Light")
        centre_btn.clicked.connect(self.centre_light)
        light_v.addWidget(centre_btn)

        colour_row = QHBoxLayout()
        colour_row.addWidget(QLabel("Colour:"))
        self.light_colour_combo = QComboBox()
        self.light_presets = [
            ("Warm White", (255, 255, 200)),
            ("Cool White", (200, 220, 255)),
            ("Sunlight",   (255, 240, 180)),
            ("UV / Blue",  (160, 180, 255)),
            ("Red",        (255, 120, 100)),
            ("Deep Green", (120, 255, 160)),
        ]
        for label, _ in self.light_presets:
            self.light_colour_combo.addItem(label)
        self.light_colour_combo.currentIndexChanged.connect(self.on_light_colour_changed)
        colour_row.addWidget(self.light_colour_combo)
        light_v.addLayout(colour_row)

        intensity_row = QHBoxLayout()
        intensity_row.addWidget(QLabel("Intensity:"))
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setRange(0, 200)
        self.intensity_slider.setValue(int(self.environment.light_intensity * 100))
        self.intensity_slider.valueChanged.connect(self.on_intensity_changed)
        intensity_row.addWidget(self.intensity_slider)
        self.intensity_label = QLabel(f"{self.environment.light_intensity:.2f}×")
        self.intensity_label.setFixedWidth(38)
        intensity_row.addWidget(self.intensity_label)
        light_v.addLayout(intensity_row)

        right_layout.addWidget(light_group)

        io_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Cell")
        self.save_btn.clicked.connect(self._save_cell_genome)
        self.save_btn.setVisible(False)
        io_layout.addWidget(self.save_btn)

        self.load_btn = QPushButton("Load Cell")
        self.load_btn.clicked.connect(self._load_cell_genome)
        self.load_btn.setVisible(False)
        io_layout.addWidget(self.load_btn)
        right_layout.addLayout(io_layout)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self._apply_gene_changes)
        self.apply_btn.setVisible(False)
        right_layout.addWidget(self.apply_btn)

        self.dna_dock = DNADock()
        self.root_layout.addWidget(self.dna_dock)

        # Replaced QTimer with decoupled thread engine
        self.simulation = SimulationEngine(self.environment)
        self.simulation.frame_ready.connect(self.update_simulation_ui)

        self.gene_rows = {}
        self._setup_gene_editor()

    def _randomise_light_source(self):
        with self.environment.lock:
            cx, cy = self.environment.center
            radius = self.environment.radius
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, radius * 0.8)
            lx = cx + math.cos(angle) * dist
            ly = cy + math.sin(angle) * dist
            self.environment.light_source = (lx, ly)

            self.environment.light_intensity = random.uniform(0.5, 1.5)
            r = random.uniform(0.7, 1.0)
            g = random.uniform(0.7, 1.0)
            b = random.uniform(0.5, 0.9)
            self.environment.light_color = (int(r*255), int(g*255), int(b*255))

            if hasattr(self, 'intensity_slider'):
                self.intensity_slider.setValue(int(self.environment.light_intensity * 100))
                self.intensity_label.setText(f"{self.environment.light_intensity:.2f}×")

    def toggle_light_enabled(self, enabled):
        with self.environment.lock:
            self.environment.light_enabled = enabled
        self.move_light_checkbox.setEnabled(enabled)
        if not enabled:
            self.move_light_checkbox.setChecked(False)
        self.renderer.update()

    def centre_light(self):
        with self.environment.lock:
            cx, cy = self.environment.center
            self.environment.light_source = (cx, cy)
        self.renderer.update()

    def on_light_colour_changed(self, index):
        _, rgb = self.light_presets[index]
        with self.environment.lock:
            self.environment.light_color = rgb
        self.renderer.update()

    def on_intensity_changed(self, value):
        intensity = value / 100.0
        with self.environment.lock:
            self.environment.light_intensity = intensity
        self.intensity_label.setText(f"{intensity:.2f}×")
        self.renderer.update()

    def _setup_gene_editor(self):
        for gene_def in GENE_FIELDS:
            name, shift, bits, scale, label, minv, maxv, step = gene_def
            is_bool = bits == 1
            is_combobox = (name == 'motility_mode')
            row = GeneRow(label, minv, maxv, step, is_bool, is_combobox)
            row.changed.connect(self._on_gene_changed)
            self.gene_rows[name] = row
            self.gene_editor_layout.addWidget(row)
        self.gene_editor_layout.addStretch()

    def _populate_gene_rows(self, cell):
        for gene_def in GENE_FIELDS:
            name = gene_def[0]
            row = self.gene_rows[name]
            row.blockSignals(True)
            if name.startswith('color_'):
                idx = {'color_r': 0, 'color_g': 1, 'color_b': 2}[name]
                row.set(cell.genome.genes['color'][idx])
            elif name == 'motility_mode':
                row.set(cell.genome.genes['motility_mode'])
            elif name == 'body_shape':
                row.set(cell.genome.genes['body_shape'])
            else:
                row.set(cell.genome.genes[name])
            row.blockSignals(False)

    def _on_gene_changed(self):
        if not getattr(self, 'selected_cell', None):
            return
        cell = self.selected_cell

        for name, row in self.gene_rows.items():
            if name.startswith('color_'):
                continue
            val = row.get()
            if name in cell.genome.genes:
                cell.genome.genes[name] = val

        r = self.gene_rows['color_r'].get()
        g = self.gene_rows['color_g'].get()
        b = self.gene_rows['color_b'].get()
        cell.genome.genes['color'] = (r, g, b)

        dna = cell.genome.encode_genes()
        self.dna_dock.set_dna(dna)
        self.renderer.update_scene()

    def _apply_gene_changes(self):
        if self.selected_cell:
            self.selected_cell.genome.encode_genes()
            self.renderer.update_scene()

    def _save_cell_genome(self):
        if not getattr(self, 'selected_cell', None):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Cell Genome", "", "Cell Files (*.cell);;All Files (*)")
        if path:
            save_genome(self.selected_cell.genome, path)

    def _load_cell_genome(self):
        if not getattr(self, 'selected_cell', None):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Cell Genome", "", "Cell Files (*.cell);;All Files (*)")
        if path:
            try:
                genome = load_genome(path)
                self.selected_cell.genome = genome
                self._populate_gene_rows(self.selected_cell)
                dna = self.selected_cell.genome.encode_genes()
                self.dna_dock.set_dna(dna)
                self.renderer.update_scene()
            except Exception as e:
                print(f"Error loading genome: {e}")

    def toggle_simulation(self):
        if self.simulation.isRunning():
            self.simulation.stop()
            self.start_button.setText("▶ Start")
            self.start_button.setStyleSheet("background-color: #2d7a2d; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px;")
        else:
            self.simulation.generate_food = self.generate_food_checkbox.isChecked()
            self.simulation.start()
            self.start_button.setText("⏹ Stop")
            self.start_button.setStyleSheet("background-color: #8b1a1a; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px;")

    def update_simulation_ui(self):
        with self.environment.lock:
            self.renderer.update_scene()
            self.cell_count_label.setText(f"Cells: {len(self.environment.cells)}")

            if hasattr(self, 'selected_cell') and self.selected_cell is not None:
                if self.selected_cell in self.environment.cells:
                    self.info_label.setText(f"{self.selected_cell.type} | Energy: {self.selected_cell.energy:.2f}")
                else:
                    self.selected_cell = None
                    self.on_cell_selected(None)

    def _random_position(self):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, self.environment.radius * 0.85)
        cx, cy = self.environment.center
        return cx + math.cos(angle) * dist, cy + math.sin(angle) * dist

    def add_random_cell(self, cell_type):
        with self.environment.lock:
            x, y = self._random_position()
            if cell_type == "bacteria":
                cell = Bacteria(Genome(), (x, y))
            elif cell_type == "phagocyte":
                cell = Phagocyte(Genome(), (x, y))
            elif cell_type == "photocyte":
                cell = Photocyte(Genome(), (x, y))
            else:
                cell = Cell(Genome(), (x, y))
            self.environment.add_cell(cell)
        self.renderer.update_scene()

    def delete_selected_cell(self):
        if hasattr(self, "selected_cell") and self.selected_cell:
            with self.environment.lock:
                self.environment.remove_cell(self.selected_cell)
            self.selected_cell = None
            self.dna_dock.set_dna(0)
            self.gene_editor_container.setVisible(False)
            self.apply_btn.setVisible(False)
            self.save_btn.setVisible(False)
            self.load_btn.setVisible(False)

    def populate_random(self):
        with self.environment.lock:
            for _ in range(3):
                self.add_random_cell("cell")
                self.add_random_cell("bacteria")
                self.add_random_cell("photocyte")
            self.add_random_cell("phagocyte")
            for _ in range(30):
                x, y = self._random_position()
                self.environment.food.append((x, y))
        self.renderer.update_scene()

    def _toggle_move_light(self, checked):
        self.renderer.move_light_mode = checked and self.environment.light_enabled

    def on_cell_selected(self, cell):
        self.selected_cell = cell
        if not cell:
            self.info_label.setText("No cell selected")
            self.info_label.setFont(self.default_info_font)
            self.dna_dock.set_dna(None)
            self.gene_editor_container.setVisible(False)
            self.apply_btn.setVisible(False)
            self.save_btn.setVisible(False)
            self.load_btn.setVisible(False)
            return

        self.info_label.setText(f"{cell.type} | Energy: {cell.energy:.2f}")
        header_font = self.info_label.font()
        header_font.setPointSize(16)
        header_font.setBold(True)
        self.info_label.setFont(header_font)
        dna = cell.genome.encode_genes()
        self.dna_dock.set_dna(dna)
        self._populate_gene_rows(cell)
        self.gene_editor_container.setVisible(True)
        self.apply_btn.setVisible(True)
        self.save_btn.setVisible(True)
        self.load_btn.setVisible(True)
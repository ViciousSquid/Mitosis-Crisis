from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QCheckBox, QSlider,
                              QGroupBox, QComboBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QColor
from renderer import Renderer
from simulation import SimulationEngine
from environment import Environment
from cell import Cell, Genome, Bacteria, Phagocyte, Photocyte
from dna_viewer import DNAViewer
import random
import math

try:
    from cell_editor import CellEditor
    _HAS_CELL_EDITOR = True
except ImportError:
    _HAS_CELL_EDITOR = False


# Light-colour presets: (label, RGB tuple)
LIGHT_PRESETS = [
    ("Warm White",   (255, 255, 200)),
    ("Cool White",   (200, 220, 255)),
    ("Sunlight",     (255, 240, 180)),
    ("UV / Blue",    (160, 180, 255)),
    ("Red",          (255, 120, 100)),
    ("Deep Green",   (120, 255, 160)),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cells — OpenGL Simulation")
        self.setGeometry(100, 100, 1280, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QHBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(6, 6, 6, 6)
        self.root_layout.setSpacing(8)

        # ---- left: simulation view ----------------------------------------
        sim_layout = QVBoxLayout()
        sim_layout.setSpacing(6)
        self.root_layout.addLayout(sim_layout, 3)

        self.environment = Environment(250)
        self.renderer = Renderer(self.environment)
        self.renderer.cell_selected.connect(self.on_cell_selected)
        sim_layout.addWidget(self.renderer, 1)

        # Controls under renderer
        ctrl_row = QHBoxLayout()
        sim_layout.addLayout(ctrl_row)

        self.cell_count_label = QLabel("Cells: 0")
        font = QFont()
        font.setPointSize(11)
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

        # Simulation controls row
        sim_ctrl_row = QHBoxLayout()
        sim_layout.addLayout(sim_ctrl_row)

        self.start_button = QPushButton("▶  Start")
        self.start_button.clicked.connect(self.toggle_simulation)
        self.start_button.setStyleSheet(
            "background-color: #2d7a2d; color: white; font-weight: bold; padding: 4px 12px;")
        sim_ctrl_row.addWidget(self.start_button)

        self.add_cell_button = QPushButton("+ Cell")
        self.add_cell_button.clicked.connect(lambda: self.add_random_cell("cell"))
        sim_ctrl_row.addWidget(self.add_cell_button)

        self.add_bacteria_button = QPushButton("+ Bacteria")
        self.add_bacteria_button.clicked.connect(lambda: self.add_random_cell("bacteria"))
        sim_ctrl_row.addWidget(self.add_bacteria_button)

        self.add_photocyte_button = QPushButton("+ Photocyte")
        self.add_photocyte_button.setStyleSheet("color: #40c060; font-weight: bold;")
        self.add_photocyte_button.clicked.connect(lambda: self.add_random_cell("photocyte"))
        sim_ctrl_row.addWidget(self.add_photocyte_button)

        self.add_phagocyte_button = QPushButton("+ Phagocyte")
        self.add_phagocyte_button.setStyleSheet("color: #e06030; font-weight: bold;")
        self.add_phagocyte_button.clicked.connect(lambda: self.add_random_cell("phagocyte"))
        sim_ctrl_row.addWidget(self.add_phagocyte_button)

        self.delete_cell_button = QPushButton("🗑 Delete")
        self.delete_cell_button.clicked.connect(self.delete_selected_cell)
        self.delete_cell_button.setEnabled(False)
        sim_ctrl_row.addWidget(self.delete_cell_button)

        self.random_button = QPushButton("🎲 Random")
        self.random_button.clicked.connect(self.populate_random)
        sim_ctrl_row.addWidget(self.random_button)

        # ---- right: panels ------------------------------------------------
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)
        self.root_layout.addLayout(right_layout, 1)

        # Light source group
        light_group = QGroupBox("☀  Light Source")
        light_group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #555;"
            " border-radius:4px; margin-top:6px; padding-top:10px;}"
            "QGroupBox::title { subcontrol-origin: margin; left:8px; }")
        light_v = QVBoxLayout(light_group)

        # Move-light toggle
        self.move_light_button = QPushButton("🖱  Drag Light Source")
        self.move_light_button.setCheckable(True)
        self.move_light_button.setToolTip(
            "Click / drag inside the petri dish to move the light source")
        self.move_light_button.toggled.connect(self.toggle_move_light)
        self.move_light_button.setStyleSheet(
            "QPushButton:checked { background-color: #b5960a; color: white; }")
        light_v.addWidget(self.move_light_button)

        # Centre-light shortcut
        centre_btn = QPushButton("⊙  Centre Light")
        centre_btn.clicked.connect(self.centre_light)
        light_v.addWidget(centre_btn)

        # Colour preset
        colour_row = QHBoxLayout()
        colour_row.addWidget(QLabel("Colour:"))
        self.light_colour_combo = QComboBox()
        for label, _ in LIGHT_PRESETS:
            self.light_colour_combo.addItem(label)
        self.light_colour_combo.currentIndexChanged.connect(self.on_light_colour_changed)
        colour_row.addWidget(self.light_colour_combo)
        light_v.addLayout(colour_row)

        # Intensity slider
        intensity_row = QHBoxLayout()
        intensity_row.addWidget(QLabel("Intensity:"))
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setRange(0, 200)
        self.intensity_slider.setValue(100)
        self.intensity_slider.setToolTip("Light intensity (0 = off, 100 = normal, 200 = bright)")
        self.intensity_slider.valueChanged.connect(self.on_intensity_changed)
        intensity_row.addWidget(self.intensity_slider)
        self.intensity_label = QLabel("1.00×")
        self.intensity_label.setFixedWidth(38)
        intensity_row.addWidget(self.intensity_label)
        light_v.addLayout(intensity_row)

        right_layout.addWidget(light_group)

        # Cell editor
        if _HAS_CELL_EDITOR:
            self.cell_editor = CellEditor()
            self.cell_editor.cell_updated.connect(self.on_cell_updated)
            right_layout.addWidget(self.cell_editor)
        else:
            self.cell_editor = None

        # DNA viewer
        self.dna_viewer = DNAViewer()
        right_layout.addWidget(self.dna_viewer)

        right_layout.addStretch()

        # ---- simulation engine -------------------------------------------
        self.simulation = SimulationEngine(self.environment)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)

    # ---------------------------------------------------------------- sim loop
    def toggle_simulation(self):
        if self.timer.isActive():
            self.timer.stop()
            self.start_button.setText("▶  Start")
            self.start_button.setStyleSheet(
                "background-color: #2d7a2d; color: white; font-weight: bold; padding: 4px 12px;")
        else:
            self.timer.start(16)   # ~60 fps
            self.start_button.setText("⏹  Stop")
            self.start_button.setStyleSheet(
                "background-color: #8b1a1a; color: white; font-weight: bold; padding: 4px 12px;")

    def update_simulation(self):
        self.simulation.update(
            generate_food=self.generate_food_checkbox.isChecked())
        self.renderer.update_scene()
        self.cell_count_label.setText(f"Cells: {len(self.environment.cells)}")

    # ---------------------------------------------------------------- cells
    def _random_position(self):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, self.environment.radius * 0.85)
        cx, cy = self.environment.center
        return cx + math.cos(angle) * dist, cy + math.sin(angle) * dist

    def add_random_cell(self, cell_type):
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
        if self.renderer.selected_cell:
            self.environment.remove_cell(self.renderer.selected_cell)
            self.renderer.selected_cell = None
            if self.cell_editor:
                self.cell_editor.set_cell(None)
            self.dna_viewer.set_cell(None)
            self.delete_cell_button.setEnabled(False)
            self.renderer.update_scene()

    def on_cell_selected(self, cell):
        if self.cell_editor:
            self.cell_editor.set_cell(cell)
        self.dna_viewer.set_cell(cell)
        self.delete_cell_button.setEnabled(cell is not None)

    def on_cell_updated(self, cell):
        # Just trigger a repaint — the renderer draws from the cell object directly
        self.renderer.update()

    def populate_random(self):
        for _ in range(3):
            self.add_random_cell("cell")
            self.add_random_cell("bacteria")
            self.add_random_cell("photocyte")
        self.add_random_cell("phagocyte")
        for _ in range(30):
            x, y = self._random_position()
            self.environment.food.append((x, y))
        self.renderer.update_scene()

    # ---------------------------------------------------------------- light
    def toggle_move_light(self, checked):
        self.renderer.move_light_mode = checked

    def centre_light(self):
        cx, cy = self.environment.center
        self.environment.light_source = (cx, cy)
        self.renderer.update()

    def on_light_colour_changed(self, index):
        _, color = LIGHT_PRESETS[index]
        self.environment.light_color = color
        self.renderer.update()

    def on_intensity_changed(self, value):
        intensity = value / 100.0
        self.environment.light_intensity = intensity
        self.intensity_label.setText(f"{intensity:.2f}×")
        self.renderer.update()

    # ---------------------------------------------------------------- key nav
    def keyPressEvent(self, event):
        step = 15
        key = event.key()
        if key == Qt.Key_W:
            self.renderer.scroll(0, -step)
        elif key == Qt.Key_A:
            self.renderer.scroll(-step, 0)
        elif key == Qt.Key_S:
            self.renderer.scroll(0, step)
        elif key == Qt.Key_D:
            self.renderer.scroll(step, 0)
        elif key == Qt.Key_Plus or key == Qt.Key_Equal:
            self.renderer.zoom_in()
        elif key == Qt.Key_Minus:
            self.renderer.zoom_out()
        else:
            super().keyPressEvent(event)

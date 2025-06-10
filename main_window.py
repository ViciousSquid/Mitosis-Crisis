from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from renderer import Renderer
from simulation import SimulationEngine
from environment import Environment
from cell import Cell, Genome, Bacteria, Phagocyte, Photocyte
from cell_editor import CellEditor
from dna_viewer import DNAViewer
import random
import math

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cells")
        self.setGeometry(100, 100, 1200, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.simulation_layout = QVBoxLayout()
        self.layout.addLayout(self.simulation_layout, 2)

        self.environment = Environment(250)  # Radius of 250
        self.renderer = Renderer(self.environment)
        self.renderer.cell_selected.connect(self.on_cell_selected)
        self.simulation_layout.addWidget(self.renderer)

        self.control_layout = QVBoxLayout()
        self.simulation_layout.addLayout(self.control_layout)

        # Cell count label at the top left with increased font size
        self.cell_count_label = QLabel("Cell Count: 0")
        font = QFont()
        font.setPointSize(14)  # Increase the font size
        self.cell_count_label.setFont(font)
        self.control_layout.addWidget(self.cell_count_label)

        # Top left control buttons and checkboxes
        self.top_left_control_layout = QHBoxLayout()
        self.control_layout.addLayout(self.top_left_control_layout)

        self.top_left_control_layout.addWidget(self.renderer.draw_food_button)
        self.top_left_control_layout.addWidget(self.renderer.erase_food_button)

        self.generate_food_checkbox = QCheckBox("Generate Food")
        self.generate_food_checkbox.setChecked(True)
        self.top_left_control_layout.addWidget(self.generate_food_checkbox)

        # Zoom buttons
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_in_button.setToolTip("Zoom in on the simulation")
        self.top_left_control_layout.addWidget(self.zoom_in_button)

        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_out_button.setToolTip("Zoom out of the simulation")
        self.top_left_control_layout.addWidget(self.zoom_out_button)

        self.main_control_layout = QHBoxLayout()
        self.control_layout.addLayout(self.main_control_layout)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.toggle_simulation)
        self.start_button.setStyleSheet("background-color: green")
        self.start_button.setToolTip("Start or stop the simulation")
        self.main_control_layout.addWidget(self.start_button)

        self.add_cell_button = QPushButton("Add Cell")
        self.add_cell_button.clicked.connect(lambda: self.add_random_cell("cell"))
        self.add_cell_button.setToolTip("Add a new random cell")
        self.main_control_layout.addWidget(self.add_cell_button)

        self.add_bacteria_button = QPushButton("Add Bacteria")
        self.add_bacteria_button.clicked.connect(lambda: self.add_random_cell("bacteria"))
        self.add_bacteria_button.setToolTip("Add a new random bacterium")
        self.main_control_layout.addWidget(self.add_bacteria_button)

        self.delete_cell_button = QPushButton("Delete Selected")
        self.delete_cell_button.clicked.connect(self.delete_selected_cell)
        self.delete_cell_button.setEnabled(False)
        self.delete_cell_button.setToolTip("Delete the currently selected cell")
        self.main_control_layout.addWidget(self.delete_cell_button)

        self.random_button = QPushButton("Random")
        self.random_button.clicked.connect(self.populate_random)
        self.random_button.setToolTip("Add a random population of cells and food")
        self.main_control_layout.addWidget(self.random_button)

        self.right_panel_layout = QVBoxLayout()
        self.layout.addLayout(self.right_panel_layout, 1)

        self.cell_editor = CellEditor()
        self.cell_editor.cell_updated.connect(self.on_cell_updated)
        self.right_panel_layout.addWidget(self.cell_editor)

        self.dna_viewer = DNAViewer()
        self.right_panel_layout.addWidget(self.dna_viewer)
        self.right_panel_layout.addStretch()  # Add stretch to push DNAViewer to the bottom

        self.simulation = SimulationEngine(self.environment)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)

    def toggle_simulation(self):
        if self.timer.isActive():
            self.timer.stop()
            self.start_button.setText("Start")
            self.start_button.setStyleSheet("background-color: green")
        else:
            self.timer.start(16)  # ~60 FPS
            self.start_button.setText("Stop")
            self.start_button.setStyleSheet("background-color: red")

    def update_simulation(self):
        self.simulation.update(
            generate_food=self.generate_food_checkbox.isChecked(),
            #allow_merge=self.merge_cells_checkbox.isChecked()
        )
        self.renderer.render()
        self.cell_count_label.setText(f"Cell Count: {len(self.environment.cells)}")

    def add_random_cell(self, cell_type):
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, self.environment.radius)
        x = self.environment.center[0] + math.cos(angle) * distance
        y = self.environment.center[1] + math.sin(angle) * distance

        if cell_type == "bacteria":
            cell = Bacteria(Genome(), (x, y))
        elif cell_type == "phagocyte":
            cell = Phagocyte(Genome(), (x, y))
        elif cell_type == "photocyte":
            cell = Photocyte(Genome(), (x, y))
        else:
            cell = Cell(Genome(), (x, y))

        self.environment.add_cell(cell)
        self.renderer.render()

    def delete_selected_cell(self):
        if self.renderer.selected_cell:
            self.environment.remove_cell(self.renderer.selected_cell)
            self.renderer.selected_cell = None
            self.cell_editor.set_cell(None)
            self.dna_viewer.set_cell(None)
            self.delete_cell_button.setEnabled(False)
            self.renderer.render()

    def on_cell_selected(self, cell):
        self.cell_editor.set_cell(cell)
        self.dna_viewer.set_cell(cell)
        self.delete_cell_button.setEnabled(cell is not None)

    def on_cell_updated(self, cell):
        self.renderer.render()

    def populate_random(self):
        for _ in range(5):
            self.add_random_cell("cell")
            self.add_random_cell("bacteria")
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, self.environment.radius)
            x = self.environment.center[0] + math.cos(angle) * distance
            y = self.environment.center[1] + math.sin(angle) * distance
            self.environment.food.append((x, y))
        self.renderer.render()

    def zoom_in(self):
        self.renderer.zoom_in()

    def zoom_out(self):
        self.renderer.zoom_out()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_W:
            self.renderer.scroll(0, -10)
        elif event.key() == Qt.Key_A:
            self.renderer.scroll(-10, 0)
        elif event.key() == Qt.Key_S:
            self.renderer.scroll(0, 10)
        elif event.key() == Qt.Key_D:
            self.renderer.scroll(10, 0)
        else:
            super().keyPressEvent(event)

# Assuming the Renderer class has the following methods:
# def zoom_in(self):
#     pass
#
# def zoom_out(self):
#     pass
#
# def scroll(self, dx, dy):
#     pass
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QLabel, QColorDialog, QCheckBox,
                             QComboBox)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal, QTimer
from cell import PhotosyntheticCell, PredatorCell, DefensiveCell, ReproductiveCell

class CellEditor(QWidget):
    cell_updated = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)

        self.cell = None
        self.gene_inputs = {}

        # General gene inputs
        for gene in ['size', 'speed', 'energy_efficiency', 'division_threshold', 'consumption_size_ratio', 'nitrogen_reserve', 'radiation_sensitivity']:
            self.gene_inputs[gene] = QLineEdit()
            self.gene_inputs[gene].setEnabled(False)
            self.form_layout.addRow(gene.replace('_', ' ').title(), self.gene_inputs[gene])

        # Color button
        self.color_button = QPushButton("Change Colour")
        self.color_button.clicked.connect(self.change_color)
        self.color_button.setEnabled(False)
        self.form_layout.addRow("Color", self.color_button)

        # Checkboxes for boolean genes
        self.has_tail_checkbox = QCheckBox("Has Tail")
        self.has_tail_checkbox.stateChanged.connect(self.update_has_tail)
        self.has_tail_checkbox.setEnabled(False)
        self.form_layout.addRow("Tail", self.has_tail_checkbox)

        self.can_consume_checkbox = QCheckBox("Can Consume")
        self.can_consume_checkbox.stateChanged.connect(self.update_can_consume)
        self.can_consume_checkbox.setEnabled(False)
        self.form_layout.addRow("Type", self.can_consume_checkbox)

        self.adhesin_checkbox = QCheckBox("Adhesin")
        self.adhesin_checkbox.stateChanged.connect(self.update_adhesin)
        self.adhesin_checkbox.setEnabled(False)
        self.form_layout.addRow("Adhesin", self.adhesin_checkbox)

        self.never_consume_checkbox = QCheckBox("Never Consume")
        self.never_consume_checkbox.stateChanged.connect(self.update_never_consume)
        self.never_consume_checkbox.setEnabled(True)
        self.form_layout.addRow("Never Consume", self.never_consume_checkbox)

        # DNA label
        self.dna_label = QLabel()
        self.form_layout.addRow("DNA", self.dna_label)

        # Energy label
        self.energy_label = QLabel()
        self.form_layout.addRow("Energy", self.energy_label)

        # Apply button
        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.apply_changes)
        self.apply_button.setEnabled(False)
        self.layout.addWidget(self.apply_button)

        # Timer to update the energy level in real-time
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_energy_label)
        self.update_timer.start(100)  # Update every 100 milliseconds

        # ComboBox for selecting cell type
        self.type_combobox = QComboBox()
        self.type_combobox.addItems(["Cell", "Predator", "Photosynthetic", "Defensive", "Reproductive"])
        self.type_combobox.currentTextChanged.connect(self.update_cell_type)
        self.form_layout.addRow("Cell Type", self.type_combobox)

        # Specific gene inputs for different cell types
        self.light_sensitivity_input = QLineEdit()
        self.light_sensitivity_input.setEnabled(False)
        self.form_layout.addRow("Light Sensitivity", self.light_sensitivity_input)

        self.hunting_efficiency_input = QLineEdit()
        self.hunting_efficiency_input.setEnabled(False)
        self.form_layout.addRow("Hunting Efficiency", self.hunting_efficiency_input)

        self.defense_strength_input = QLineEdit()
        self.defense_strength_input.setEnabled(False)
        self.form_layout.addRow("Defense Strength", self.defense_strength_input)

        self.reproduction_rate_input = QLineEdit()
        self.reproduction_rate_input.setEnabled(False)
        self.form_layout.addRow("Reproduction Rate", self.reproduction_rate_input)

    def set_cell(self, cell):
        self.cell = cell
        if cell:
            # Round numeric values to make them more user-readable
            for gene, input_field in self.gene_inputs.items():
                value = cell.genome.genes[gene]
                if isinstance(value, (int, float)):
                    value = round(value, 2)  # Round to 2 decimal places
                input_field.setText(str(value))
                input_field.setEnabled(True)

            # Set color button background
            color = QColor.fromRgbF(*cell.genome.genes['color'])
            self.color_button.setStyleSheet(f"background-color: rgb({color.red()}, {color.green()}, {color.blue()})")
            self.color_button.setEnabled(True)

            # Set checkboxes
            self.has_tail_checkbox.setChecked(cell.genome.genes['has_tail'])
            self.has_tail_checkbox.setEnabled(True)
            self.can_consume_checkbox.setChecked(cell.genome.genes['can_consume'])
            self.can_consume_checkbox.setEnabled(True)
            self.adhesin_checkbox.setChecked(cell.genome.genes['adhesin'])
            self.adhesin_checkbox.setEnabled(True)

            # Set DNA label
            self.dna_label.setText(f"{cell.dna:08X}")

            # Enable apply button
            self.apply_button.setEnabled(True)

            # Update energy label
            self.update_energy_label()

            # Set cell type
            self.type_combobox.setCurrentText(cell.type)

            # Set specific gene inputs based on cell type
            if isinstance(cell, PhotosyntheticCell):
                self.light_sensitivity_input.setText(str(round(cell.light_sensitivity, 2)))
                self.light_sensitivity_input.setEnabled(True)
            else:
                self.light_sensitivity_input.setText("")
                self.light_sensitivity_input.setEnabled(False)

            if isinstance(cell, PredatorCell):
                self.hunting_efficiency_input.setText(str(round(cell.hunting_efficiency, 2)))
                self.hunting_efficiency_input.setEnabled(True)
            else:
                self.hunting_efficiency_input.setText("")
                self.hunting_efficiency_input.setEnabled(False)

            if isinstance(cell, DefensiveCell):
                self.defense_strength_input.setText(str(round(cell.defense_strength, 2)))
                self.defense_strength_input.setEnabled(True)
            else:
                self.defense_strength_input.setText("")
                self.defense_strength_input.setEnabled(False)

            if isinstance(cell, ReproductiveCell):
                self.reproduction_rate_input.setText(str(round(cell.reproduction_rate, 2)))
                self.reproduction_rate_input.setEnabled(True)
            else:
                self.reproduction_rate_input.setText("")
                self.reproduction_rate_input.setEnabled(False)

        else:
            # Clear and disable all fields
            for input_field in self.gene_inputs.values():
                input_field.clear()
                input_field.setEnabled(False)
            self.color_button.setStyleSheet("")
            self.color_button.setEnabled(False)
            self.has_tail_checkbox.setChecked(False)
            self.has_tail_checkbox.setEnabled(False)
            self.can_consume_checkbox.setChecked(False)
            self.can_consume_checkbox.setEnabled(False)
            self.adhesin_checkbox.setChecked(False)
            self.adhesin_checkbox.setEnabled(False)
            self.dna_label.clear()
            self.energy_label.clear()
            self.apply_button.setEnabled(False)
            self.type_combobox.setCurrentText("Cell")
            self.light_sensitivity_input.clear()
            self.light_sensitivity_input.setEnabled(False)
            self.hunting_efficiency_input.clear()
            self.hunting_efficiency_input.setEnabled(False)
            self.defense_strength_input.clear()
            self.defense_strength_input.setEnabled(False)
            self.reproduction_rate_input.clear()
            self.reproduction_rate_input.setEnabled(False)

    def apply_changes(self):
        if self.cell:
            for gene, input_field in self.gene_inputs.items():
                self.cell.genome.genes[gene] = float(input_field.text())
            self.cell.genome.never_consume = self.never_consume_checkbox.isChecked()
            self.cell_updated.emit(self.cell)

            # Update specific gene inputs based on cell type
            if isinstance(self.cell, PhotosyntheticCell):
                self.cell.light_sensitivity = float(self.light_sensitivity_input.text())
            if isinstance(self.cell, PredatorCell):
                self.cell.hunting_efficiency = float(self.hunting_efficiency_input.text())
            if isinstance(self.cell, DefensiveCell):
                self.cell.defense_strength = float(self.defense_strength_input.text())
            if isinstance(self.cell, ReproductiveCell):
                self.cell.reproduction_rate = float(self.reproduction_rate_input.text())

    def change_color(self):
        if self.cell:
            color = QColorDialog.getColor()
            if color.isValid():
                self.cell.genome.genes['color'] = (color.redF(), color.greenF(), color.blueF())
                self.color_button.setStyleSheet(f"background-color: {color.name()}")
                self.cell_updated.emit(self.cell)

    def update_has_tail(self, state):
        if self.cell:
            self.cell.genome.genes['has_tail'] = bool(state)
            self.cell_updated.emit(self.cell)

    def update_can_consume(self, state):
        if self.cell:
            self.cell.genome.genes['can_consume'] = bool(state)
            self.cell_updated.emit(self.cell)

    def update_adhesin(self, state):
        if self.cell:
            self.cell.genome.genes['adhesin'] = bool(state)
            self.cell_updated.emit(self.cell)

    def update_never_consume(self, state):
        if self.cell:
            if state == 2:  # Checked
                self.can_consume_checkbox.setEnabled(False)
                self.cell.genome.never_consume = True
            else:
                self.can_consume_checkbox.setEnabled(True)
                self.cell.genome.never_consume = False
            self.cell_updated.emit(self.cell)

    def update_energy_label(self):
        if self.cell:
            self.energy_label.setText(f"Energy: {round(self.cell.energy, 2):.2f}")

    def update_cell_type(self, type_name):
        if self.cell:
            self.cell.type = type_name
            self.cell_updated.emit(self.cell)
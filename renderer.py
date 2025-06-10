from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsEllipseItem, QGraphicsPolygonItem, QToolButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtGui import QColor, QPen, QPainter, QPolygonF
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
import math

class CellItem(QGraphicsItem):
    def __init__(self, cell):
        super().__init__()
        self.cell = cell
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def boundingRect(self):
        size = max(self.cell.genome.genes['size'], 15)
        extra = 0
        if self.cell.genome.genes['has_tail']:
            extra = size * 1.5
        if self.cell.adhesin:
            extra = max(extra, 20)
        
        return QRectF(-size/2 - extra, -size/2 - extra, size + extra*2, size + extra*2)

    def paint(self, painter, option, widget):
        painter.setPen(QPen(Qt.black, 0.5))
        color = QColor.fromRgbF(*self.cell.genome.genes['color'])
        size = max(self.cell.genome.genes['size'], 15)

        if self.cell.adhesin:
            adhesin_size = size + 20
            adhesin_color = QColor(color)
            adhesin_color.setAlpha(100)
            painter.setBrush(adhesin_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(-adhesin_size / 2, -adhesin_size / 2, adhesin_size, adhesin_size))

        painter.setBrush(color)
        painter.setPen(QPen(Qt.black, 0.5))
        painter.drawEllipse(QRectF(-size / 2, -size / 2, size, size))

        if self.cell.genome.genes['has_tail']:
            tail_length = size * 1.5
            angle = self.cell.angle
            tail_end_x = math.cos(angle) * tail_length
            tail_end_y = math.sin(angle) * tail_length

            tail_polygon = QPolygonF([
                QPointF(0, 0),
                QPointF(-size / 4, -size / 4),
                QPointF(tail_end_x, tail_end_y),
                QPointF(size / 4, -size / 4)
            ])
            painter.setBrush(color)
            painter.drawPolygon(tail_polygon)

        if self.isSelected():
            pen = QPen(Qt.red, 3)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(-size / 2, -size / 2, size, size))

class Renderer(QGraphicsView):
    cell_selected = pyqtSignal(object)

    def __init__(self, environment, parent=None):
        super().__init__(parent)
        self.environment = environment
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.selected_cell = None
        self.draw_food_mode = False
        self.erase_food_mode = False

        self.cell_items = {}
        self.food_items = {}

        self.draw_food_button = QToolButton()
        self.draw_food_button.setText("Draw Food")
        self.draw_food_button.setCheckable(True)
        self.draw_food_button.clicked.connect(self.toggle_draw_food_mode)

        self.erase_food_button = QToolButton()
        self.erase_food_button.setText("Erase Food")
        self.erase_food_button.setCheckable(True)
        self.erase_food_button.clicked.connect(self.toggle_erase_food_mode)

        self.tool_layout = QVBoxLayout()
        self.tool_layout.addWidget(self.draw_food_button)
        self.tool_layout.addWidget(self.erase_food_button)

        self.tool_widget = QWidget()
        self.tool_widget.setLayout(self.tool_layout)
        self.tool_widget.setFixedWidth(100)

        self.energy_label = QLabel()
        self.tool_layout.addWidget(self.energy_label)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.boundary_item = QGraphicsEllipseItem(0, 0, self.environment.radius * 2, self.environment.radius * 2)
        self.boundary_item.setPen(QPen(Qt.black, 2))
        self.scene.addItem(self.boundary_item)

    def update_scene(self):
        current_cell_ids = set()
        for cell in self.environment.cells:
            current_cell_ids.add(cell.id)
            if cell.id in self.cell_items:
                cell_item = self.cell_items[cell.id]
                cell_item.setPos(cell.position[0], cell.position[1])
                cell_item.update()
            else:
                self.add_cell_item(cell)

        removed_ids = self.cell_items.keys() - current_cell_ids
        for cell_id in removed_ids:
            self.scene.removeItem(self.cell_items[cell_id])
            del self.cell_items[cell_id]

        current_food_pos = set(self.environment.food)
        for pos in current_food_pos:
            if pos not in self.food_items:
                food_item = QGraphicsEllipseItem(pos[0] - 1, pos[1] - 1, 2, 2)
                food_item.setBrush(Qt.green)
                self.scene.addItem(food_item)
                self.food_items[pos] = food_item

        removed_food = self.food_items.keys() - current_food_pos
        for pos in removed_food:
            self.scene.removeItem(self.food_items[pos])
            del self.food_items[pos]

        if self.selected_cell:
            self.energy_label.setText(f"Energy: {self.selected_cell.energy:.2f}")

    def add_cell_item(self, cell):
        cell_item = CellItem(cell)
        cell_item.setPos(cell.position[0], cell.position[1])
        self.scene.addItem(cell_item)
        self.cell_items[cell.id] = cell_item

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, CellItem):
                if self.selected_cell and self.selected_cell.id in self.cell_items:
                    self.cell_items[self.selected_cell.id].setSelected(False)

                self.selected_cell = item.cell
                item.setSelected(True)
                self.cell_selected.emit(item.cell)
            else:
                if self.selected_cell and self.selected_cell.id in self.cell_items:
                    self.cell_items[self.selected_cell.id].setSelected(False)
                self.selected_cell = None
                self.cell_selected.emit(None)

            if self.draw_food_mode:
                pos = self.mapToScene(event.pos())
                self.environment.food.append((pos.x(), pos.y()))
                self.update_scene()
            elif self.erase_food_mode:
                pos = self.mapToScene(event.pos())
                for food in self.environment.food[:]:
                    x, y = food
                    if math.sqrt((pos.x() - x) ** 2 + (pos.y() - y) ** 2) < 5:
                        self.environment.food.remove(food)
                        self.update_scene()
                        break
        super().mousePressEvent(event)

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

    def mouseMoveEvent(self, event):
        if self.selected_cell and self.cell_items[self.selected_cell.id].isUnderMouse():
             pos = self.mapToScene(event.pos())
             self.selected_cell.position = (pos.x(), pos.y())
             self.cell_items[self.selected_cell.id].setPos(pos)
        else:
            super().mouseMoveEvent(event)

    def zoom_in(self):
        self.scale(1.2, 1.2)

    def zoom_out(self):
        self.scale(1 / 1.2, 1 / 1.2)

    def scroll(self, dx, dy):
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + dx)
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + dy)
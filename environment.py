import random
import math
from cell import Cell, Genome, Phagocyte, Photocyte


class Quadtree:
    def __init__(self, boundary, capacity):
        self.boundary = boundary
        self.capacity = capacity
        self.cells = []
        self.divided = False

    def subdivide(self):
        x, y, w, h = self.boundary
        half_w, half_h = w / 2, h / 2
        self.ne = Quadtree((x + half_w, y,         half_w, half_h), self.capacity)
        self.nw = Quadtree((x,          y,         half_w, half_h), self.capacity)
        self.se = Quadtree((x + half_w, y + half_h, half_w, half_h), self.capacity)
        self.sw = Quadtree((x,          y + half_h, half_w, half_h), self.capacity)
        self.divided = True

    def insert(self, cell):
        if not self.contains(cell.position):
            return False
        if len(self.cells) < self.capacity:
            self.cells.append(cell)
            return True
        if not self.divided:
            self.subdivide()
        return (self.ne.insert(cell) or self.nw.insert(cell)
                or self.se.insert(cell) or self.sw.insert(cell))

    def query(self, aabb, found_cells=None):
        if found_cells is None:
            found_cells = []
        if not self.intersects(aabb):
            return found_cells
        for cell in self.cells:
            if self.aabb_contains(aabb, cell.position):
                found_cells.append(cell)
        if self.divided:
            for child in (self.nw, self.ne, self.sw, self.se):
                child.query(aabb, found_cells)
        return found_cells

    def contains(self, pos):
        x, y, w, h = self.boundary
        return x <= pos[0] < x + w and y <= pos[1] < y + h

    def aabb_contains(self, aabb, pos):
        x, y, w, h = aabb
        return x <= pos[0] < x + w and y <= pos[1] < y + h

    def intersects(self, aabb):
        bx, by, bw, bh = self.boundary
        ax, ay, aw, ah = aabb
        return not (ax > bx + bw or ax + aw < bx or ay > by + bh or ay + ah < by)


class Environment:
    def __init__(self, radius):
        self.radius = radius
        self.center = (radius, radius)
        self.cells = []
        self.food = []
        self.food_generation_rate = 5
        self.max_food = 1000
        self.current_time = 0
        self.starvation_threshold = 1000
        self.wrap_around = False
        self.quadtree_boundary = (0, 0, radius * 2, radius * 2)

        # Light source — start at centre of dish
        self.light_source = (radius, radius)
        self.light_color = (255, 255, 200)   # warm white
        self.light_intensity = 1.0            # 0–2 range

    def add_cell(self, cell):
        self.cells.append(cell)

    def remove_cell(self, cell):
        if cell in self.cells:
            self.cells.remove(cell)

    def update(self, dt, generate_food=True, allow_merge=False):
        self.current_time += dt

        for cell in self.cells[:]:
            cell.update(self, dt)
            if cell.energy <= 0.72 or cell.nitrogen_reserve <= 0.1 or cell.age >= 240:
                cell.die(self)
            elif cell.can_divide():
                new_cell = cell.divide()
                self.add_cell(new_cell)
            elif cell.genome.genes['size'] >= cell.max_size:
                new_cell = cell.divide()
                self.add_cell(new_cell)

        # Quadtree collision
        qtree = Quadtree(self.quadtree_boundary, 4)
        for cell in self.cells:
            qtree.insert(cell)

        for cell1 in self.cells:
            size1 = cell1.genome.genes['size']
            aoi = (cell1.position[0] - size1, cell1.position[1] - size1,
                   size1 * 2, size1 * 2)
            for cell2 in qtree.query(aoi):
                if cell1 is cell2:
                    continue
                if not cell1.check_collision(cell2):
                    continue
                if allow_merge and cell1.type == cell2.type and \
                        cell1 in self.cells and cell2 in self.cells:
                    self.merge_cells(cell1, cell2)
                elif isinstance(cell1, Phagocyte) and cell1.can_consume(cell2):
                    cell1.consume(cell2, self)
                    if cell2 in self.cells:
                        self.remove_cell(cell2)
                elif isinstance(cell2, Phagocyte) and cell2.can_consume(cell1):
                    cell2.consume(cell1, self)
                    if cell1 in self.cells:
                        self.remove_cell(cell1)
                else:
                    cell1.resolve_collision(cell2)

        if generate_food:
            food_to_generate = self.food_generation_rate * dt
            while food_to_generate > 0 and len(self.food) < self.max_food:
                if random.random() < food_to_generate:
                    angle = random.uniform(0, 2 * math.pi)
                    distance = random.uniform(0, self.radius)
                    x = self.center[0] + math.cos(angle) * distance
                    y = self.center[1] + math.sin(angle) * distance
                    self.food.append((x, y))
                food_to_generate -= 1

        for cell in self.cells:
            for food in self.food[:]:
                dist = math.hypot(cell.position[0] - food[0],
                                  cell.position[1] - food[1])
                if dist < cell.genome.genes['size']:
                    cell.energy += 5
                    cell.last_eaten = self.current_time
                    self.food.remove(food)

    def merge_cells(self, cell1, cell2):
        new_genome = Genome()
        for gene in new_genome.genes:
            if isinstance(new_genome.genes[gene], bool):
                new_genome.genes[gene] = (cell1.genome.genes[gene]
                                           or cell2.genome.genes[gene])
            elif isinstance(new_genome.genes[gene], tuple):
                new_genome.genes[gene] = tuple(
                    (a + b) / 2
                    for a, b in zip(cell1.genome.genes[gene],
                                    cell2.genome.genes[gene]))
            else:
                new_genome.genes[gene] = (cell1.genome.genes[gene]
                                           + cell2.genome.genes[gene]) / 2
        new_genome.genes['size'] = (cell1.genome.genes['size']
                                     + cell2.genome.genes['size'])
        new_pos = ((cell1.position[0] + cell2.position[0]) / 2,
                   (cell1.position[1] + cell2.position[1]) / 2)
        new_cell = Cell(new_genome, new_pos)
        new_cell.energy = cell1.energy + cell2.energy
        new_cell.nitrogen_reserve = (cell1.nitrogen_reserve
                                      + cell2.nitrogen_reserve) / 2
        new_cell.type = cell1.type
        self.remove_cell(cell1)
        self.remove_cell(cell2)
        self.add_cell(new_cell)

    def get_state(self):
        return {
            'cells': [(cell.position, cell.genome.genes['size'],
                       cell.genome.genes['color'],
                       cell.genome.genes['has_tail'], cell.angle)
                      for cell in self.cells],
            'food': self.food
        }

import random
import math
from cell import Cell, Genome, PredatorCell, PhotosyntheticCell, DefensiveCell, ReproductiveCell

class Environment:
    def __init__(self, radius):
        self.radius = radius
        self.center = (radius, radius)
        self.cells = []
        self.food = []
        self.food_generation_rate = 5
        self.max_food = 1000
        self.current_time = 0  # Track the current time
        self.starvation_threshold = 1000  # Default value 1000
        self.wrap_around = False  # New attribute to control wrapping behavior
        self.light_source = (radius, radius)  # Center of the environment as a light source

    def add_cell(self, cell):
        self.cells.append(cell)

    def remove_cell(self, cell):
        if cell in self.cells:
            self.cells.remove(cell)
        else:
            print(f"Attempted to remove a cell that is not in the list: {cell}")

    def resolve_boundary_collision(self, cell):
        if self.wrap_around:
            # Wrap around the edges
            cell.position = (
                (cell.position[0] - self.center[0] + self.radius) % (2 * self.radius) + self.center[0],
                (cell.position[1] - self.center[1] + self.radius) % (2 * self.radius) + self.center[1]
            )
        else:
            # Default behavior: bounce back from the boundary
            distance = math.sqrt((cell.position[0] - self.center[0]) ** 2 + (cell.position[1] - self.center[1]) ** 2)
            if distance > self.radius - cell.genome.genes['size'] / 2:
                angle = math.atan2(self.center[1] - cell.position[1], self.center[0] - cell.position[0])
                new_x = self.center[0] + math.cos(angle) * (self.radius - cell.genome.genes['size'] / 2)
                new_y = self.center[1] + math.sin(angle) * (self.radius - cell.genome.genes['size'] / 2)
                cell.position = (new_x, new_y)

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

        for i, cell in enumerate(self.cells):
            for other_cell in self.cells[i + 1:]:
                distance = math.sqrt((cell.position[0] - other_cell.position[0]) ** 2 +
                                     (cell.position[1] - other_cell.position[1]) ** 2)
                if distance < (cell.genome.genes['size'] + other_cell.genome.genes['size']) / 2:
                    if allow_merge and cell.type == other_cell.type:
                        self.merge_cells(cell, other_cell)
                    elif isinstance(cell, PredatorCell) and cell.can_consume(other_cell):
                        cell.consume(other_cell, self)
                        self.remove_cell(other_cell)
                    elif isinstance(other_cell, PredatorCell) and other_cell.can_consume(cell):
                        other_cell.consume(cell, self)
                        self.remove_cell(cell)

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
                distance = math.sqrt((cell.position[0] - food[0]) ** 2 + (cell.position[1] - food[1]) ** 2)
                if distance < cell.genome.genes['size']:
                    cell.energy += 5
                    cell.last_eaten = self.current_time  # Update the last eaten time
                    self.food.remove(food)

        # Update specific behaviors for different cell types
        for cell in self.cells:
            if isinstance(cell, PhotosyntheticCell):
                cell.photosynthesize(self, dt)
            elif isinstance(cell, PredatorCell):
                cell.hunt(self)
            elif isinstance(cell, DefensiveCell):
                cell.defend(self)
            elif isinstance(cell, ReproductiveCell):
                cell.reproduce(self)

    def merge_cells(self, cell1, cell2):
        # Create a new cell with combined properties
        new_genome = Genome()
        for gene in new_genome.genes:
            if isinstance(new_genome.genes[gene], bool):
                new_genome.genes[gene] = cell1.genome.genes[gene] or cell2.genome.genes[gene]
            elif isinstance(new_genome.genes[gene], tuple):
                new_genome.genes[gene] = tuple((a + b) / 2 for a, b in zip(cell1.genome.genes[gene], cell2.genome.genes[gene]))
            else:
                new_genome.genes[gene] = (cell1.genome.genes[gene] + cell2.genome.genes[gene]) / 2

        # Set the new cell's size to the sum of the two original cells
        new_genome.genes['size'] = cell1.genome.genes['size'] + cell2.genome.genes['size']

        # Create the new cell at the midpoint between the two original cells
        new_position = (
            (cell1.position[0] + cell2.position[0]) / 2,
            (cell1.position[1] + cell2.position[1]) / 2
        )
        new_cell = Cell(new_genome, new_position)
        new_cell.energy = cell1.energy + cell2.energy
        new_cell.nitrogen_reserve = (cell1.nitrogen_reserve + cell2.nitrogen_reserve) / 2
        new_cell.type = cell1.type  # Assuming same type cells are merging

        # Remove the original cells and add the new merged cell
        self.remove_cell(cell1)
        self.remove_cell(cell2)
        self.add_cell(new_cell)

    def get_state(self):
        return {
            'cells': [(cell.position, cell.genome.genes['size'], cell.genome.genes['color'],
                       cell.genome.genes['has_tail'], cell.angle) for cell in self.cells],
            'food': self.food
        }
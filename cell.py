import random
import math
import uuid
import numpy as np


class Genome:
    def __init__(self, genes=None, never_consume=False):
        self.genes = genes or {
            'size': random.uniform(5, 20),
            'speed': random.uniform(0.5, 2.0),
            'energy_efficiency': random.uniform(0.5, 1.5),
            'division_threshold': random.uniform(20, 40),
            'color': (random.random(), random.random(), random.random()),
            'has_tail': random.choice([True, False]),
            'can_consume': random.choice([True, False]),
            'consumption_size_ratio': random.uniform(1.2, 2.0),
            'nitrogen_reserve': random.uniform(0.2, 0.5),
            'adhesin': random.choice([True, False]),
            'radiation_sensitivity': random.uniform(0.1, 0.5)
        }
        self.dna = self.encode_genes()
        self.never_consume = never_consume

    def encode_genes(self):
        dna = 0
        dna |= (int(self.genes['size'] * 10) & 0xFF) << 24
        dna |= (int(self.genes['speed'] * 10) & 0xFF) << 16
        dna |= (int(self.genes['energy_efficiency'] * 10) & 0xFF) << 8
        dna |= (int(self.genes['division_threshold'] * 10) & 0xFF)
        dna |= (int(self.genes['consumption_size_ratio'] * 10) & 0xFF) << 32
        dna |= (int(self.genes['color'][0] * 255) & 0xFF) << 40
        dna |= (int(self.genes['color'][1] * 255) & 0xFF) << 48
        dna |= (int(self.genes['color'][2] * 255) & 0xFF) << 56
        dna |= (int(self.genes['has_tail']) & 0x1) << 64
        dna |= (int(self.genes['can_consume']) & 0x1) << 65
        dna |= (int(self.genes['nitrogen_reserve'] * 10) & 0xFF) << 72
        dna |= (int(self.genes['adhesin']) & 0x1) << 80
        dna |= (int(self.genes['radiation_sensitivity'] * 10) & 0xFF) << 88
        return dna

    def decode_genes(self, dna):
        self.genes['size'] = ((dna >> 24) & 0xFF) / 10.0
        self.genes['speed'] = ((dna >> 16) & 0xFF) / 10.0
        self.genes['energy_efficiency'] = ((dna >> 8) & 0xFF) / 10.0
        self.genes['division_threshold'] = (dna & 0xFF) / 10.0
        self.genes['consumption_size_ratio'] = ((dna >> 32) & 0xFF) / 10.0
        self.genes['color'] = (
            ((dna >> 40) & 0xFF) / 255.0,
            ((dna >> 48) & 0xFF) / 255.0,
            ((dna >> 56) & 0xFF) / 255.0
        )
        self.genes['has_tail'] = (dna >> 64) & 0x1
        self.genes['can_consume'] = (dna >> 65) & 0x1
        self.genes['nitrogen_reserve'] = ((dna >> 72) & 0xFF) / 10.0
        self.genes['adhesin'] = (dna >> 80) & 0x1
        self.genes['radiation_sensitivity'] = ((dna >> 88) & 0xFF) / 10.0

    def mutate(self, mutation_rate=0.1):
        for gene in self.genes:
            if random.random() < mutation_rate:
                if isinstance(self.genes[gene], bool):
                    if gene == 'can_consume' and self.never_consume:
                        continue
                    self.genes[gene] = not self.genes[gene]
                elif isinstance(self.genes[gene], tuple):
                    self.genes[gene] = tuple(
                        min(1, max(0, x + random.uniform(-0.1, 0.1)))
                        for x in self.genes[gene])
                else:
                    self.genes[gene] *= random.uniform(0.8, 1.2)

    def copy(self):
        return Genome(self.genes.copy(), self.never_consume)


class Cell:
    def __init__(self, genome, position, dna=None):
        self.id = uuid.uuid4()
        self.genome = genome
        self.position = np.array(position, dtype=float)
        self.energy = 20
        self.age = 0
        self.dna = dna or self.genome.encode_genes()
        self.angle = random.uniform(0, 2 * math.pi)
        self.type = "Cell"
        self.nitrogen_reserve = self.genome.genes['nitrogen_reserve']
        self.adhesin = self.genome.genes['adhesin']
        self.radiation_sensitivity = self.genome.genes['radiation_sensitivity']
        self.last_eaten = 0
        self.adhered_cells = []
        self.max_size = 32

        # Animation state
        self.pulse_phase = random.uniform(0, 2 * math.pi)
        # Smooth turn tracking
        self._target_angle = self.angle
        self._turn_speed = random.uniform(1.5, 3.0)  # radians/sec
        # Membrane wobble accumulators
        self._wobble_offset = np.zeros(2)

    def _steer_toward(self, target_pos, dt):
        """Smoothly steer toward a world position."""
        direction = np.array(target_pos) - self.position
        dist = np.linalg.norm(direction)
        if dist < 1.0:
            return
        desired_angle = math.atan2(direction[1], direction[0])
        # Shortest-arc turn
        diff = (desired_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        max_turn = self._turn_speed * dt
        self.angle += max(-max_turn, min(max_turn, diff))

    def update(self, environment, dt):
        self.age += dt
        self.energy += self.genome.genes['energy_efficiency'] * dt

        # Energy cost: size + movement overhead
        size = self.genome.genes['size']
        self.energy -= size * 0.012 * dt
        self.energy -= size * 0.018 * dt  # locomotion cost

        # Forced division at max size
        if size >= self.max_size:
            self.divide()

        self.nitrogen_reserve += 0.01 * dt
        self.energy -= self.radiation_sensitivity * dt

        # Movement: tailed cells go straight (with slight wander), others drift
        if self.genome.genes['has_tail']:
            # Gentle random wander
            self.angle += random.gauss(0, 0.05)
            speed = self.genome.genes['speed']
            velocity = np.array([math.cos(self.angle),
                                  math.sin(self.angle)]) * speed * dt
        else:
            # Brownian drift
            velocity = np.random.uniform(-1, 1, 2) * self.genome.genes['speed'] * dt

        self.position += velocity

        # Energy cost from movement
        distance_moved = np.linalg.norm(velocity)
        self.energy -= distance_moved * 0.1

        self.resolve_boundary_collision(environment)

        if self.energy <= 0:
            self.genome.genes['color'] = (0.5, 0.5, 0.5)
            self.die(environment)
            return

        # Starvation
        if environment.current_time - self.last_eaten > environment.starvation_threshold:
            self.die(environment)
            return

        # Scale size by energy
        self.genome.genes['size'] = max(5, min(128, self.energy * 0.5))

        # Cap energy
        self.energy = min(100, self.energy)

        # Energy sharing with adhered cells
        if self.adhesin and self.adhered_cells:
            total = self.energy + sum(c.energy for c in self.adhered_cells)
            avg = total / (len(self.adhered_cells) + 1)
            self.energy = avg
            for c in self.adhered_cells:
                c.energy = avg

    def can_divide(self):
        return (self.age >= 20
                and self.energy > self.genome.genes['division_threshold']
                and self.nitrogen_reserve >= 0.2)

    def divide(self):
        child_genome = self.genome.copy()
        child_genome.mutate()
        offset = np.array([random.choice([-8, 8]), random.choice([-8, 8])])
        child_position = self.position + offset
        child_dna = (self.dna & 0xFFFF0000) | (random.randint(0, 65535) & 0x0000FFFF)
        child = Cell(child_genome, child_position, child_dna)
        child.type = self.type
        self.energy /= 2
        child.energy = self.energy
        self.nitrogen_reserve /= 2
        child.nitrogen_reserve = self.nitrogen_reserve
        self.genome.genes['size'] /= 2
        child.genome.genes['size'] = self.genome.genes['size']
        return child

    def can_consume(self, other_cell):
        if self.type == "Phagocyte" and other_cell.type == "Bacteria":
            return True
        if not self.genome.genes['can_consume']:
            return False
        size_ratio = self.genome.genes['size'] / other_cell.genome.genes['size']
        return size_ratio > self.genome.genes['consumption_size_ratio']

    def consume(self, other_cell, environment):
        self.energy += other_cell.energy
        self.nitrogen_reserve += other_cell.nitrogen_reserve
        self.genome.genes['size'] += other_cell.genome.genes['size'] * 0.1
        self.genome.genes['size'] = min(self.genome.genes['size'], 32)
        self.last_eaten = environment.current_time
        self.energy = min(100, self.energy)

    def die(self, environment):
        distance = np.linalg.norm(self.position - np.array(environment.center))
        if distance <= environment.radius:
            environment.food.append(tuple(self.position))
        if self in environment.cells:
            environment.remove_cell(self)

    def adhere_to(self, other_cell):
        if self.adhesin and other_cell.adhesin and other_cell not in self.adhered_cells:
            self.adhered_cells.append(other_cell)
            other_cell.adhered_cells.append(self)

    def separate_from(self, other_cell):
        if other_cell in self.adhered_cells:
            self.adhered_cells.remove(other_cell)
            other_cell.adhered_cells.remove(self)

    def check_collision(self, other_cell):
        distance = np.linalg.norm(self.position - other_cell.position)
        return distance < (self.genome.genes['size'] + other_cell.genome.genes['size']) / 2

    def resolve_collision(self, other_cell):
        distance = np.linalg.norm(self.position - other_cell.position)
        if distance < 0.001:
            distance = 0.001
        overlap = (self.genome.genes['size'] + other_cell.genome.genes['size']) / 2 - distance
        if overlap > 0:
            direction = (other_cell.position - self.position) / distance
            self.position -= direction * overlap / 2
            other_cell.position += direction * overlap / 2

    def resolve_boundary_collision(self, environment):
        center_vec = np.array(environment.center)
        distance_vec = self.position - center_vec
        distance = np.linalg.norm(distance_vec)
        limit = environment.radius - self.genome.genes['size'] / 2
        if distance > limit:
            if environment.wrap_around:
                self.position = (self.position - center_vec) % (
                    2 * environment.radius) + center_vec - environment.radius
            else:
                direction = distance_vec / distance
                self.position = center_vec + direction * limit
                # Reflect angle off boundary
                normal = -direction
                dot = (math.cos(self.angle) * normal[0]
                       + math.sin(self.angle) * normal[1])
                self.angle = math.atan2(
                    math.sin(self.angle) - 2 * dot * normal[1],
                    math.cos(self.angle) - 2 * dot * normal[0])


# ---------------------------------------------------------------------------
class Bacteria(Cell):
    """Fast, small, erratic bacterium."""

    def __init__(self, genome, position, dna=None):
        super().__init__(genome, position, dna)
        self.type = "Bacteria"
        self.genome.genes['size'] *= 0.5
        self.genome.genes['speed'] *= 1.5
        self.genome.genes['energy_efficiency'] *= 0.8
        self.genome.genes['has_tail'] = True
        self._tumble_timer = random.uniform(0.5, 2.0)

    def update(self, environment, dt):
        # Run-and-tumble locomotion (realistic bacterial motility)
        self._tumble_timer -= dt
        if self._tumble_timer <= 0:
            # Tumble: random new direction
            self.angle = random.uniform(0, 2 * math.pi)
            self._tumble_timer = random.uniform(0.3, 1.5)

        super().update(environment, dt)

        # Random energy burst for division pressure
        if random.random() < 0.001:
            self.energy = self.genome.genes['division_threshold']

        self.energy = min(100, self.energy)


# ---------------------------------------------------------------------------
class Phagocyte(Cell):
    """Predatory cell that hunts and engulfs Bacteria."""

    def __init__(self, genome, position, dna=None):
        super().__init__(genome, position, dna)
        self.type = "Phagocyte"
        self.genome.genes['size'] = max(self.genome.genes['size'], 12)
        self.genome.genes['speed'] *= 0.8
        self.genome.genes['has_tail'] = True
        self._hunt_target = None
        self._hunt_search_timer = 0.0

    def update(self, environment, dt):
        self._hunt_search_timer -= dt

        # Re-evaluate nearest bacterium periodically
        if self._hunt_search_timer <= 0:
            self._hunt_target = self._find_nearest_prey(environment)
            self._hunt_search_timer = random.uniform(0.3, 0.8)

        if self._hunt_target is not None and self._hunt_target in environment.cells:
            self._steer_toward(self._hunt_target.position, dt)
        else:
            self._hunt_target = None
            # Slow wander when idle
            self.angle += random.gauss(0, 0.08)

        super().update(environment, dt)

    def _find_nearest_prey(self, environment):
        best, best_dist = None, float('inf')
        for cell in environment.cells:
            if cell is self:
                continue
            if cell.type == "Bacteria":
                dist = np.linalg.norm(self.position - cell.position)
                if dist < best_dist:
                    best_dist = dist
                    best = cell
        return best


# ---------------------------------------------------------------------------
class Photocyte(Cell):
    """Photosynthetic cell — seeks the light source and gains energy from it."""

    # Chlorophyll-green tint
    _BASE_COLOR = (0.15, 0.75, 0.25)

    def __init__(self, genome, position, dna=None):
        super().__init__(genome, position, dna)
        self.type = "Photocyte"
        # Override colour to a green family
        r, g, b = self._BASE_COLOR
        self.genome.genes['color'] = (
            r + random.uniform(-0.08, 0.08),
            g + random.uniform(-0.12, 0.12),
            b + random.uniform(-0.08, 0.08),
        )
        self.genome.genes['has_tail'] = True
        self.genome.genes['speed'] *= 0.7
        self.glow_intensity = 0.0   # read by renderer for the glow effect
        self._light_timer = 0.0

    def update(self, environment, dt):
        lx, ly = environment.light_source
        intensity = getattr(environment, 'light_intensity', 1.0)

        # Steer toward light source
        self._steer_toward((lx, ly), dt)

        # Distance to light
        dist_to_light = math.hypot(self.position[0] - lx,
                                   self.position[1] - ly)
        light_factor = max(0.0, 1.0 - dist_to_light / environment.radius)
        self.glow_intensity = light_factor * intensity

        # Photosynthesis energy bonus — proportional to light exposure
        photo_gain = light_factor * intensity * 3.5 * dt
        self.energy += photo_gain

        # Slow growth in light — chloroplast accumulation
        if light_factor > 0.4:
            growth = light_factor * 0.08 * dt
            self.genome.genes['size'] = min(
                self.genome.genes['size'] + growth, 30)
            # Deepen to darker green when thriving
            r, g, b = self.genome.genes['color']
            self.genome.genes['color'] = (
                max(0.05, r - 0.003 * dt),
                min(0.90, g + 0.005 * dt),
                max(0.05, b - 0.002 * dt),
            )
        elif light_factor < 0.1:
            # Bleach (etiolation) when starved of light
            r, g, b = self.genome.genes['color']
            self.genome.genes['color'] = (
                min(0.8, r + 0.002 * dt),
                max(0.3, g - 0.004 * dt),
                min(0.6, b + 0.002 * dt),
            )

        if photo_gain > 0:
            self.last_eaten = environment.current_time

        super().update(environment, dt)

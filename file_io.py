import json
from cell import Cell, Genome
from environment import Environment

def save_environment(environment, filename):
    data = {
        'radius': environment.radius,
        'cells': [
            {
                'position': list(cell.position),
                'energy': cell.energy,
                'age': cell.age,
                'genome': cell.genome.genes,
                'type': cell.type
            }
            for cell in environment.cells
        ],
        'food': environment.food
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_environment(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    environment = Environment(data['radius'])
    environment.food = data['food']

    for cell_data in data['cells']:
        genes = cell_data.get('genome', {})
        # Ensure new keys exist (backward compat)
        if 'motility_mode' not in genes:
            genes['motility_mode'] = 1 if genes.get('has_tail', True) else 0
        if 'body_shape' not in genes:
            genes['body_shape'] = 0
        if 'has_tail' in genes:
            del genes['has_tail']   # no longer used
        genome = Genome(genes)

        cell_type = cell_data.get('type', 'Cell')
        if cell_type == 'Bacteria':
            from cell import Bacteria
            cell = Bacteria(genome, cell_data['position'])
        elif cell_type == 'Phagocyte':
            from cell import Phagocyte
            cell = Phagocyte(genome, cell_data['position'])
        elif cell_type == 'Photocyte':
            from cell import Photocyte
            cell = Photocyte(genome, cell_data['position'])
        else:
            cell = Cell(genome, cell_data['position'])

        cell.energy = cell_data['energy']
        cell.age = cell_data['age']
        environment.add_cell(cell)

    return environment

def save_genome(genome, filename):
    with open(filename, 'w') as f:
        json.dump(genome.genes, f, indent=2)

def load_genome(filename):
    with open(filename, 'r') as f:
        genes = json.load(f)
    return Genome(genes)
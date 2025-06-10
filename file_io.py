# file_io.py
import json
from cell import Cell, Genome
from environment import Environment

def save_environment(environment, filename):
    data = {
        'radius': environment.radius,
        'cells': [
            {
                'position': cell.position,
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
        json.dump(data, f)

def load_environment(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    
    environment = Environment(data['radius'])
    environment.food = data['food']
    
    for cell_data in data['cells']:
        genome = Genome(cell_data['genome'])
        
        # We need to determine the correct cell class to instantiate
        cell_type = cell_data.get('type', 'Cell') # Default to 'Cell' if type isn't saved
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
        json.dump(genome.genes, f)

def load_genome(filename):
    with open(filename, 'r') as f:
        genes = json.load(f)
    return Genome(genes)
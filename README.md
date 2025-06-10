# Cells - A Cell Simulation

This is a work-in-progress cell simulation built with Python and PyQt5. You can observe cells as they live, move, eat, divide, and evolve in a contained environment.

![image](https://github.com/user-attachments/assets/97867ee2-afd8-4d69-8fc8-d05a8c10684e)

## Features

* **Multiple Cell Types:** Simulate different types of cells like Bacteria, Phagocytes, and Photocytes.
* **Genetics:** Each cell has a unique genome that determines its characteristics, which can mutate upon division.
* **Interactive Environment:** Add or remove cells and food, and watch the simulation unfold.
* **Cell Editor:** Select individual cells to view and edit their genes in real-time.
* **Save/Load:** Save the state of your simulation and load it later to continue your experiments.

## Getting Started

### Prerequisites

* Python 3
* pip (Python package installer)

### Installation

1.  Clone this repository to your local machine.
2.  Navigate to the project directory in your terminal.
3.  Install the required packages using the `requirements.txt` file:

    ```bash
    pip install -r requirements.txt
    ```

### Running the Simulation

To start the simulation, run the `main.py` file:

```bash
python main.py
```

## How to Use

* **Start/Stop:** Use the "Start" and "Stop" button to control the simulation.
* **Add Cells:** Use the "Add Cell" and "Add Bacteria" buttons to introduce new cells into the environment.
* **Select a Cell:** Click on a cell to select it. Its information will be displayed in the right-hand panel.
* **Edit Genes:** With a cell selected, you can modify its genes in the "Cell Editor" and click "Apply Changes".
* **Navigate the View:**
    * Use the **WASD** keys to pan the view.
    * Use the "Zoom In" and "Zoom Out" buttons to change the magnification.
    * Click and drag the background to move the view.

---
*This is a WIP project.*
import time
from PyQt5.QtCore import QThread, pyqtSignal

class SimulationEngine(QThread):
    frame_ready = pyqtSignal()

    def __init__(self, environment):
        super().__init__()
        self.environment = environment
        self.time_step = 0.016  # Target 60 FPS update rate
        self.simulation_speed = 1.0
        self._is_running = False
        self.generate_food = True
        self.allow_merge = False

    def run(self):
        self._is_running = True
        while self._is_running:
            start_time = time.perf_counter()

            # Acquire lock before modifying state
            with self.environment.lock:
                self.environment.update(self.time_step, self.generate_food, self.allow_merge)

            # Signal GUI to render
            self.frame_ready.emit()

            # Manage tick rate
            elapsed = time.perf_counter() - start_time
            target_delay = self.time_step / self.simulation_speed
            sleep_time = target_delay - elapsed

            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self):
        self._is_running = False
        self.wait()

    def fast_forward(self, speed_factor):
        self.simulation_speed = speed_factor

    def slow_motion(self, speed_factor):
        self.simulation_speed = 1 / speed_factor

    def reset_speed(self):
        self.simulation_speed = 1.0
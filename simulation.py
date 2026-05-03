import time
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


class SimulationEngine(QThread):
    """
    Runs the environment update loop on a background thread.

    The simulation ticks at up to ~60 Hz but only emits `frame_ready`
    when the GUI has finished processing the previous frame (tracked by
    `_gui_busy`).  This prevents signal-queue flooding when the sim is
    faster than the renderer can keep up.
    """
    frame_ready = pyqtSignal()

    def __init__(self, environment):
        super().__init__()
        self.environment = environment
        self.time_step = 0.016          # Target 60 FPS update rate
        self.simulation_speed = 1.0
        self._is_running = False
        self.generate_food = True
        self.allow_merge = False

        # Frame-skip guard — prevents queuing dozens of frame_ready
        # signals while the GUI is still painting.
        self._gui_busy_mutex = QMutex()
        self._gui_busy = False

    # Called by the GUI thread when it starts processing a frame
    def mark_gui_busy(self):
        self._gui_busy_mutex.lock()
        self._gui_busy = True
        self._gui_busy_mutex.unlock()

    # Called by the GUI thread when it finishes processing a frame
    def mark_gui_idle(self):
        self._gui_busy_mutex.lock()
        self._gui_busy = False
        self._gui_busy_mutex.unlock()

    def run(self):
        self._is_running = True
        while self._is_running:
            start_time = time.perf_counter()

            # Acquire environment lock, run one simulation tick
            with self.environment.lock:
                self.environment.update(self.time_step, self.generate_food, self.allow_merge)

            # Only signal the GUI if it isn't still processing the last frame
            self._gui_busy_mutex.lock()
            gui_busy = self._gui_busy
            if not gui_busy:
                self._gui_busy = True      # pre-mark busy
            self._gui_busy_mutex.unlock()

            if not gui_busy:
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

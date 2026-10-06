"""Observe original RK stage states without changing evolution or source code."""
import numpy as np

RK_WEIGHTS = (1 / 6, 1 / 6, 2 / 3)


def allocation_observer(source_class, setup, *, q_aa, q_at, dt):
    class AllocationObserver(source_class):
        def __init__(self):
            super().__init__(setup, "V2_RUN", q_aa=q_aa, q_at=q_at)
            self.stage_count = 0
            self.cumulative_faces = {}
            self.capture_stage = False

        def _face_diagnostics(self, state):
            x, y = super()._face_diagnostics(state)
            if self.capture_stage:
                weight = dt * RK_WEIGHTS[self.stage_count % 3]
                for axis, fields in (("x_faces", x), ("y_faces", y)):
                    for channel in ("bg", "aa", "at"):
                        key = f"{axis}_pi_{channel}"
                        if key not in self.cumulative_faces:
                            self.cumulative_faces[key] = np.zeros_like(fields[f"pi_{channel}"])
                        self.cumulative_faces[key] += weight * fields[f"pi_{channel}"]
            return x, y

        def observe_stage(self, state):
            self.capture_stage = True
            try:
                result = super().observe_stage(state)
            finally:
                self.capture_stage = False
            self.stage_count += 1
            return result

    return AllocationObserver()

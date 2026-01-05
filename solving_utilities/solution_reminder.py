"""A dataclass which stores the variable values and the objective value of a solution."""

import dataclasses


@dataclasses.dataclass(frozen=True)
class SolutionReminder:
    objective_value: int
    assign_students_var_values: tuple[int | float, ...]

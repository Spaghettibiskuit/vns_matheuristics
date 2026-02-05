"""Class that stores the solution's objective as well as the values of the assignment variables."""

import dataclasses


@dataclasses.dataclass(frozen=True)
class SolutionReminder:
    """Stores the solution's objective as well as the values of the assignment variables."""

    objective_value: int
    assign_students_var_values: tuple[int | float, ...]

"""A class that provides actions and checks needed during local branching and assignment fixing."""

import abc
import time

from model_wrappers.thin_wrappers import Initializer
from solving_utilities.callbacks import Patience
from utilities import Stations, gurobi_round


class ModelWrapper(abc.ABC):
    """Provides actions and checks needed during both local branching and assignment fixing."""

    def __init__(self, initializer: Initializer):
        self._model_components = initializer.model_components
        self._model = initializer.model
        self._start_time = initializer.start_time
        self._solution_summaries = initializer.solution_summaries
        self._current_solution = initializer.current_solution
        self._best_found_solution = initializer.current_solution
        self._assign_students_vars = tuple(
            self._model_components.variables.assign_students.values()
        )

    @property
    def model_components(self):
        """The model's variables, the linear expressions of the objective, and the constraints."""
        return self._model_components

    @property
    def solution_summaries(self):
        """Recordings at the point of time when a new best solution was found.

        Those consist of the following:
            - The objective value,
            - the time elapsed when it was found,
            - whether it was found during VND,shake or initial_optimization,
            - and how many shakes had already occurred before.
        """
        return self._solution_summaries

    @property
    def objective_value(self) -> int:
        """The objective value of the solution in the model."""
        return gurobi_round(self._model.ObjVal)

    @property
    def solution_count(self) -> int:
        """The solution count in the last solver run."""
        return self._model.SolCount

    def set_time_limit(self, total_time_limit: int | float):
        """Ensure that the solver does not run longer than the total time limit allows."""
        self._model.Params.TimeLimit = max(0, total_time_limit - (time.time() - self._start_time))

    def optimize(self, patience: int | float, shake: bool = False) -> None:
        """Optimize with a given patience while recording new best solutions.

        Args:
            patience: The time the solver is allowed to run without finding improvements. See
                below for further information.
            shake: Is the current optimization in a shake or not. Only matters for the recording
                of new best solutions. If shake is True, it will be noted that a new best solution
                was found during a shake. Otherwise it is recorded as found during VND.

        Example for patience:
        If the patience were 5 seconds and the solver were to find an improvement every 4 seconds,
        the solver run would never stop, unless there is a separate, hard time limit. If only once
        no improvement is found within 5 seconds, the solver run terminates.

        Patience does not apply during preprocessing:
        The patience only applies once the progress information on the branch-and-cut tree search
        is displayed, since only then Gurobi potentially finds improvements. Any preprocessing is
        allowed to run as long as it takes.
        """
        callback = Patience(
            patience=patience,
            start_time=self._start_time,
            solution_summaries=self.solution_summaries,
            station=Stations.SHAKE if shake else Stations.VND,
            best_obj=max(
                self._best_found_solution.objective_value, self._current_solution.objective_value
            ),
        )
        self._model.optimize(callback)
        if self.solution_count > 0 and self.objective_value > callback.best_obj:
            summary: dict[str, int | float | str] = {
                "objective": self.objective_value,
                "runtime": time.time() - self._start_time,
                "station": Stations.SHAKE if shake else Stations.VND,
                "shakes": self._model.Params.Seed,
            }
            self.solution_summaries.append(summary)

    def new_best_found(self) -> bool:
        """Return whether the current solution is the best yet in this run of the algorithm."""
        return self._current_solution.objective_value > self._best_found_solution.objective_value

    def increment_random_seed(self) -> None:
        """Increase the random seed of the Gurobi model by 1."""
        self._model.Params.Seed += 1

    def improvement_found(self) -> bool:
        """Return whether the solution in the model is the best yet in the current VND."""
        return self.objective_value > self._current_solution.objective_value

    def recover_to_best_found(self) -> None:
        """Make Gurobi get back to the best solution in this run of the algorithm.

        Fix all assignment variable values at those of the best solution. Let Gurobi figure out the
        according value of the rest of the variables, which is computationally rather inexpensive.
        """
        assignment_var_values = self._best_found_solution.assign_students_var_values
        self._model.setAttr("LB", self._assign_students_vars, assignment_var_values)
        self._model.setAttr("UB", self._assign_students_vars, assignment_var_values)

        self._model.Params.TimeLimit = float("inf")
        self._model.optimize()

    @abc.abstractmethod
    def store_solution(self) -> None:
        """Store the data necessary to recreate it and to use it as a reference point."""

    @abc.abstractmethod
    def make_current_solution_best_solution(self) -> None:
        """If a new best solution was found during shake or VND, save it as such."""

    @abc.abstractmethod
    def make_best_solution_current_solution(self) -> None:
        """Make the best solution the reference point before the shake."""

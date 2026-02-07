"""2 classes: One performs the initial optimization, the other is for running Gurobi alone."""

import functools
import time

import utilities
from modeling.base_model_builder import BaseModelBuilder
from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from solving_utilities.assignment_fixing_data import AssignmentFixingData
from solving_utilities.callbacks import GurobiAloneProgressTracker, Patience
from solving_utilities.solution_reminder import SolutionReminder


class Initializer:
    """For initial optimization and as the basis for constructing LocalBrancher or AssignmentFixer.

    Local Brancher and AssignmentFixer both need a first solution to be instantiated.
    AssignmentFixer additionally needs an instance of AssignmentFixingData to know which variables
    to fix. Instances of this class are used to obtain those prerequisites.

    Attributes:
        config: Data that defines the problem instance.
        derived: Iterables and hash-table backed containers useful during optimization that are
            derived from config.
        model_components: The model variables, the linear expressions that make up the objective,
            as well as the constraints of the model.
        model: A Gurobi model.
        start_time: The epoch right after the model was built.
        solution_summaries: Recordings at the point of time when a new best solution was found.
            Those consist of the following:
            - The objective value,
            - the time elapsed when it was found,
            - whether it was found during VND,shake or initial_optimization,
            - and how many shakes had already occurred before.
    """

    def __init__(
        self, config: Configuration, derived: DerivedModelingData, required_solution_count: int
    ):
        self.config = config
        self.derived = derived
        self.model_components, self.model = BaseModelBuilder(
            config=self.config, derived=self.derived
        ).get_base_model()
        self.start_time = time.time()
        self.solution_summaries: list[dict[str, int | float | str]] = []
        self._required_solution_count = required_solution_count

    def set_time_limit(self, total_time_limit: int | float) -> None:
        """Ensure that the solver does not run longer than the total time limit allows."""
        self.model.Params.TimeLimit = max(0, total_time_limit - (time.time() - self.start_time))

    def optimize(self, patience: int | float) -> None:
        """Optimize with a given patience while recording new best solutions.

        Args:
            patience: The time the solver is allowed to run without finding improvements. See
                below for further information.

        Example for patience:
        If the patience were 5 seconds and the solver were to find an improvement every 4 seconds,
        the solver run would never stop, unless there is a separate, hard time limit. If only once
        no improvement is found within 5 seconds, the solver run terminates.

        Patience does not apply during preprocessing:
        The patience only applies once the progress information on the branch-and-cut tree
        search is displayed, since only then Gurobi potentially finds improvements. Any
        preprocessing is allowed to run as long as it takes.
        """
        callback = Patience(
            patience=patience,
            solution_summaries=self.solution_summaries,
            start_time=self.start_time,
            station=utilities.Stations.INITIAL_OPTIMIZATION,
            required_solution_count=self._required_solution_count,
        )
        self.model.optimize(callback)
        if (obj := utilities.gurobi_round(self.model.ObjVal)) > callback.best_obj:
            summary: dict[str, int | float | str] = {
                "objective": obj,
                "runtime": time.time() - self.start_time,
                "station": utilities.Stations.INITIAL_OPTIMIZATION,
                "shakes": self.model.Params.Seed,
            }
            self.solution_summaries.append(summary)

    @functools.cached_property
    def current_solution(self) -> SolutionReminder:
        """The objective value and assignment variable values for the best solution yet."""
        variables = self.model_components.variables
        return SolutionReminder(
            objective_value=utilities.gurobi_round(self.model.ObjVal),
            assign_students_var_values=utilities.var_values(variables.assign_students.values()),
        )

    @functools.cached_property
    def fixing_data(self) -> AssignmentFixingData:
        """The data to know which variables to fix according to the assignment fixing algorithm."""
        return AssignmentFixingData.get(
            config=self.config,
            derived=self.derived,
            variables=self.model_components.variables,
            lin_expressions=self.model_components.lin_expressions,
            model=self.model,
        )


class GurobiAloneWrapper:
    """For running Gurobi without any further algorithm.

    Attributes:
        model_components: The model variables, the linear expressions that make up the objective,
            as well as the constraints of the model.
        model: A Gurobi model.
        start_time: The epoch right after the model was built.
        solution_summaries: Recordings at the point of time when a new best solution was found.
            Those consist of the following:
            - The objective value,
            - the time elapsed when it was found,
            - whether it was found during VND,shake or initial_optimization,
            - and how many shakes had already occurred before.
    """

    def __init__(self, config: Configuration, derived: DerivedModelingData):
        self.model_components, self.model = BaseModelBuilder(config, derived).get_base_model()
        self.start_time = time.time()
        self.solution_summaries: list[dict[str, int | float]] = []

    @property
    def objective_value(self) -> int:
        """The objective value of the solution in the model."""
        return utilities.gurobi_round(self.model.ObjVal)

    def set_time_limit(self, time_limit: int | float) -> None:
        """Ensure that the solver does not run longer than the total time limit allows."""
        self.model.Params.TimeLimit = time_limit

    def optimize(self) -> None:
        """Optimize while recording new best solutions and lowerings of the upper bound."""
        self.model.optimize(GurobiAloneProgressTracker(self.start_time, self.solution_summaries))
        summary: dict[str, int | float] = {
            "objective": utilities.gurobi_round(self.model.ObjVal),
            "bound": utilities.gurobi_round(self.model.ObjBound),
            "runtime": time.time() - self.start_time,
        }
        self.solution_summaries.append(summary)

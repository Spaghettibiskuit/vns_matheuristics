import abc
import time

import gurobipy

from modeling.model_components import ModelComponents
from solving_utilities.callbacks import Patience
from solving_utilities.solution_reminder import SolutionReminder
from utilities import Stations, gurobi_round


class ModelWrapper(abc.ABC):

    def __init__(
        self,
        model_components: ModelComponents,
        model: gurobipy.Model,
        start_time: float,
        solution_summaries: list[dict[str, int | float | str]],
        sol_reminder: SolutionReminder,
    ):
        self.model_components = model_components
        self.model = model
        self.start_time = start_time
        self.solution_summaries = solution_summaries
        self.current_solution = sol_reminder
        self.best_found_solution = sol_reminder
        self.assign_students_vars = tuple(self.model_components.variables.assign_students.values())

    @property
    def status(self) -> int:
        return self.model.Status

    @property
    def bound(self) -> int:
        return int(min(self.model.ObjBound, gurobipy.GRB.MAXINT) + 1e-4)

    @property
    def objective_value(self) -> int:
        return gurobi_round(self.model.ObjVal)

    @property
    def solution_count(self) -> int:
        return self.model.SolCount

    def eliminate_time_limit(self):
        self.model.Params.TimeLimit = float("inf")

    def set_time_limit(self, total_time_limit: int | float, start_time: float):
        self.model.Params.TimeLimit = max(0, total_time_limit - (time.time() - start_time))

    def optimize(self, patience: int | float, required_sol_count: int = 0, shake: bool = False):
        callback = Patience(
            patience=patience,
            start_time=self.start_time,
            best_obj=max(
                self.best_found_solution.objective_value, self.current_solution.objective_value
            ),
            solution_summaries=self.solution_summaries,
            station=Stations.SHAKE if shake else Stations.VND,
            required_sol_count=required_sol_count,
        )
        self.model.optimize(callback)
        if self.solution_count > 0 and self.objective_value > callback.best_obj:
            summary: dict[str, int | float | str] = {
                "objective": self.objective_value,
                "runtime": time.time() - self.start_time,
                "station": Stations.SHAKE if shake else Stations.VND,
                "shakes": self.model.Params.Seed,
            }
            self.solution_summaries.append(summary)

    def new_best_found(self) -> bool:
        return self.current_solution.objective_value > self.best_found_solution.objective_value

    def increment_random_seed(self):
        self.model.Params.Seed += 1

    def improvement_infeasible(self) -> bool:
        return self.bound <= self.current_solution.objective_value

    def improvement_found(self) -> bool:
        return self.objective_value > self.current_solution.objective_value

    def recover_to_best_found(self):

        assignment_var_values = self.best_found_solution.assign_students_var_values
        self.model.setAttr("LB", self.assign_students_vars, assignment_var_values)
        self.model.setAttr("UB", self.assign_students_vars, assignment_var_values)

        self.eliminate_time_limit()
        self.model.optimize()

    @abc.abstractmethod
    def store_solution(self):
        pass

    @abc.abstractmethod
    def make_current_solution_best_solution(self):
        pass

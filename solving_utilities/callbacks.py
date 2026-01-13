"""Callback classes which terminate solving when no better solution was found in given time."""

import time

import gurobipy
from gurobipy import GRB

from utilities import Stations, gurobi_round


class GurobiAloneProgressTracker:
    """Tracks the progress of Gurobi"""

    def __init__(self, start_time: float, solution_summaries: list[dict[str, int | float]]):
        self.best_obj = -GRB.MAXINT
        self.best_bound = GRB.MAXINT
        self.start_time = start_time
        self.solution_summaries = solution_summaries

    def __call__(self, model: gurobipy.Model, where: int):
        if where == GRB.Callback.MIPSOL:
            current_objective = gurobi_round(model.cbGet(GRB.Callback.MIPSOL_OBJ))
            best_bound = min(GRB.MAXINT, gurobi_round(model.cbGet(GRB.Callback.MIPSOL_OBJBND)))

            if current_objective > self.best_obj or best_bound < self.best_bound:
                self.best_obj = current_objective
                self.best_bound = best_bound

                summary: dict[str, int | float] = {
                    "objective": current_objective,
                    "bound": best_bound,
                    "runtime": time.time() - self.start_time,
                }
                self.solution_summaries.append(summary)


class Patience:
    def __init__(
        self,
        patience: float | int,
        start_time: float,
        solution_summaries: list[dict[str, int | float | str]],
        station: Stations,
        best_obj: int = -GRB.MAXINT,
        required_sol_count: int = 0,
    ):
        self.reference_time: float | None = None
        self.patience = patience
        self.start_time = start_time
        self.solution_summaries = solution_summaries
        self.station = station
        self.best_obj = best_obj
        self.required_sol_count = required_sol_count
        self.sol_count = 0

    def __call__(self, model: gurobipy.Model, where: int):
        if not self.reference_time:
            if where == GRB.Callback.MESSAGE and model.cbGet(GRB.Callback.MSG_STRING).startswith(
                "    Nodes"
            ):
                self.reference_time = time.time()

        elif where == GRB.Callback.MIPSOL:
            self.reference_time = time.time()
            current_objective = gurobi_round(model.cbGet(GRB.Callback.MIPSOL_OBJ))

            if current_objective > self.best_obj:
                self.best_obj = current_objective
                summary: dict[str, int | float | str] = {
                    "objective": current_objective,
                    "runtime": self.reference_time - self.start_time,
                    "station": self.station,
                    "shakes": model.Params.Seed,
                }
                self.solution_summaries.append(summary)

            self.sol_count += 1

        elif (
            self.sol_count >= self.required_sol_count
            and time.time() - self.reference_time > self.patience
        ):
            model.terminate()

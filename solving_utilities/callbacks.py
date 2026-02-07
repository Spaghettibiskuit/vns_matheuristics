"""One callback class for Gurobi used alone, another for local branching or assignment fixing."""

import time

import gurobipy
from gurobipy import GRB

from utilities import Stations, gurobi_round


class GurobiAloneProgressTracker:
    """Records whenever a new best solution was found or the upper bound was lowered.

    Knowing that solutions can only be integer valued, a lower upper bound is only found if
    floor(bound) has been lowered. Every record consists of the objective, the bound and the time
    elapsed since building the model was finished. Those records are stored in the
    solution_summaries passed to the constructor.
    """

    def __init__(self, start_time: float, solution_summaries: list[dict[str, int | float]]):
        self._best_obj = -GRB.MAXINT
        self._best_bound = GRB.MAXINT
        self._start_time = start_time
        self._solution_summaries = solution_summaries

    def __call__(self, model: gurobipy.Model, where: int):
        if where == GRB.Callback.MIPSOL:
            current_objective = gurobi_round(model.cbGet(GRB.Callback.MIPSOL_OBJ))
            best_bound = min(GRB.MAXINT, gurobi_round(model.cbGet(GRB.Callback.MIPSOL_OBJBND)))

            if current_objective > self._best_obj or best_bound < self._best_bound:
                self._best_obj = current_objective
                self._best_bound = best_bound

                summary: dict[str, int | float] = {
                    "objective": current_objective,
                    "bound": best_bound,
                    "runtime": time.time() - self._start_time,
                }
                self._solution_summaries.append(summary)


class Patience:
    """Records new best solutions and stops optimization if no improvement found in given time.

    The optimization is stopped when for x seconds no improvement to the current solution was
    found. The x is called patience and is passed to the constructor.

    Patience does not apply during preprocessing:
    The patience only applies once the progress information on the branch-and-cut tree search is
    displayed, since only then Gurobi potentially finds improvements. Any preprocessing is allowed
    to run as long as it takes.

    The current solution may be worse than the best solution found yet if there was a shake in
    between. Only new best solutions are recorded.

    Each record includes the following:
    - The objective value
    - The time elapsed since building the model was finished
    - The station in the algorithm the solution was found: Initial optimization, VND or Shake
    - The number of shakes that preceded the finding of that solution
    """

    def __init__(
        self,
        patience: float | int,
        start_time: float,
        solution_summaries: list[dict[str, int | float | str]],
        station: Stations,
        best_obj: int = -GRB.MAXINT,
        required_solution_count: int = 0,
    ):
        self._reference_time: float | None = None
        self._patience = patience
        self._start_time = start_time
        self._solution_summaries = solution_summaries
        self._station = station
        self._best_obj = best_obj
        self._required_solution_count = required_solution_count
        self._sol_count = 0

    def __call__(self, model: gurobipy.Model, where: int) -> None:
        if not self._reference_time:
            if where == GRB.Callback.MESSAGE and model.cbGet(GRB.Callback.MSG_STRING).startswith(
                "    Nodes"  # progress information on the branch-and-cut tree search is displayed
            ):
                self._reference_time = time.time()

        elif where == GRB.Callback.MIPSOL:
            self._reference_time = time.time()
            current_objective = gurobi_round(model.cbGet(GRB.Callback.MIPSOL_OBJ))

            if current_objective > self._best_obj:
                self._best_obj = current_objective
                summary: dict[str, int | float | str] = {
                    "objective": current_objective,
                    "runtime": self._reference_time - self._start_time,
                    "station": self._station,
                    "shakes": model.Params.Seed,
                }
                self._solution_summaries.append(summary)

            self._sol_count += 1

        elif (
            self._sol_count >= self._required_solution_count
            and time.time() - self._reference_time > self._patience
        ):
            model.terminate()

    @property
    def best_obj(self) -> int:
        """The best objective known to the callback.

        Used to check after the optimization whether a better objective was reached which was
        not recorded in the callback.
        """
        return self._best_obj

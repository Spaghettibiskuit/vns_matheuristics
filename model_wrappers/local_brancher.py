"""A class mainly to construct, add, and remove branching constraints.

It also provides checks relevant to the control flow inside local branching.
"""

import itertools

import gurobipy

import utilities
from model_wrappers.model_wrapper import ModelWrapper
from model_wrappers.thin_wrappers import Initializer
from solving_utilities.solution_reminder import SolutionReminder


class LocalBrancher(ModelWrapper):
    """Offers commands to construct branching constraints and to add or remove them from the model.

    Also provides checks relevant to the control flow inside local branching.
    """

    def __init__(self, initializer: Initializer):
        super().__init__(initializer)
        self._branching_constraints: list[gurobipy.Constr] = []
        self._shake_constraints: tuple[gurobipy.Constr, gurobipy.Constr] | None = None
        self._counter = itertools.count()

    @property
    def bound(self) -> int:
        """The best (lowest) bound for the objective value."""
        return int(min(self._model.ObjBound, gurobipy.GRB.MAXINT) + 1e-4)

    def solution_is_optimal(self) -> bool:
        """Return whether it is optimal within the bounding constraint."""
        return self._model.Status == gurobipy.GRB.OPTIMAL

    def improvement_infeasible(self) -> bool:
        """Return wether improvement is impossible within the bounding constraint."""
        return self.bound <= self._current_solution.objective_value

    def store_solution(self) -> None:
        self._current_solution = SolutionReminder(
            objective_value=self.objective_value,
            assign_students_var_values=utilities.var_values(self._assign_students_vars),
        )

    def make_current_solution_best_solution(self) -> None:
        self._best_found_solution = self._current_solution

    def make_best_solution_current_solution(self) -> None:
        self._current_solution = self._best_found_solution

    def branching_lin_expression(self) -> gurobipy.LinExpr:
        """Return the LinExpr whose value is the hamming distance to the current solution."""
        return gurobipy.quicksum(
            1 - var if var_value > 0.5 else var
            for var, var_value in zip(
                self._assign_students_vars,
                self._current_solution.assign_students_var_values,
            )
        )

    def add_bounding_branching_constraint(self, rhs: int) -> None:
        """Only allow a hamming distance <= rhs to the current solution."""
        branching_constr_name = f"branching{next(self._counter)}"
        branching_constr = self._model.addConstr(
            self.branching_lin_expression() <= rhs,
            name=branching_constr_name,
        )
        self._branching_constraints.append(branching_constr)

    def pop_branching_constraints_stack(self) -> None:
        """Remove the branching constraint on top of the stack."""
        branching_constraint = self._branching_constraints.pop()
        self._model.remove(branching_constraint)

    def add_excluding_branching_constraint(self, rhs: int) -> None:
        """Only allow a hamming distance >= rhs + 1 to the current solution."""
        branching_constr_name = f"branching{next(self._counter)}"
        branching_constr = self._model.addConstr(
            self.branching_lin_expression() >= rhs + 1,
            name=branching_constr_name,
        )
        self._branching_constraints.append(branching_constr)

    def drop_all_branching_constraints(self) -> None:
        """Remove every constraint that was not part of the base model."""
        self._model.remove(self._branching_constraints)
        self._branching_constraints.clear()

    def add_shaking_constraints(self, k_cur: int, k_step: int) -> None:
        """Only allow hamming distance h with k_cur <= h <= k_cur + k_step to the best solution.

        The current solution has to point to the best solution when this method is called.
        """
        lin_expr = self.branching_lin_expression()
        smaller_radius = self._model.addConstr(
            lin_expr >= k_cur,
        )
        bigger_radius = self._model.addConstr(
            lin_expr <= k_cur + k_step,
        )

        self._shake_constraints = smaller_radius, bigger_radius

    def remove_shaking_constraints(self) -> None:
        """Remove the shaking constraints once the shake is over."""
        if self._shake_constraints is None:
            raise TypeError("Cannot remove shake constraints if None.")
        self._model.remove(self._shake_constraints)
        self._shake_constraints = None

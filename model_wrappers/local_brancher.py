"""A class mainly to construct, add, and remove branching constraints.

It also allows to save key data on solutions and provides checks specific to local branching.
"""

import itertools

import gurobipy

import utilities
from model_wrappers.model_wrapper import ModelWrapper
from model_wrappers.thin_wrappers import Initializer
from modeling.model_components import ModelComponents
from solving_utilities.solution_reminder import SolutionReminder


class LocalBrancher(ModelWrapper):
    """Offers commands to construct branching constraints and to add or remove them from the model.

    Also allows to save key data on solutions and provides checks specific to local branching.

    Attributes additional to ModelWrapper:
        branching_constraints: A stack of constraints. A new branching constraint is laid on top.
        shake_constraints: Two constraints present during the shake which act like concentric
            circles between which solutions are allowed.
        counter: used to create unique branching constraint names.
    """

    def __init__(
        self,
        model_components: ModelComponents,
        model: gurobipy.Model,
        start_time: float,
        solution_summaries: list[dict[str, int | float | str]],
        sol_reminder: SolutionReminder,
    ):
        super().__init__(
            model_components=model_components,
            model=model,
            start_time=start_time,
            solution_summaries=solution_summaries,
            sol_reminder=sol_reminder,
        )

        self.branching_constraints: list[gurobipy.Constr] = []
        self.shake_constraints: tuple[gurobipy.Constr, gurobipy.Constr] | None = None
        self.counter = itertools.count()

    @property
    def status(self) -> int:
        """The optimization status code of the Gurobi model."""
        return self.model.Status

    @property
    def bound(self) -> int:
        """The best (lowest) bound for the objective value."""
        return int(min(self.model.ObjBound, gurobipy.GRB.MAXINT) + 1e-4)

    def improvement_infeasible(self) -> bool:
        """Return wether improvement is impossible within the bounding constraint."""
        return self.bound <= self.current_solution.objective_value

    def store_solution(self) -> None:
        self.current_solution = SolutionReminder(
            objective_value=self.objective_value,
            assign_students_var_values=utilities.var_values(self.assign_students_vars),
        )

    def make_current_solution_best_solution(self) -> None:
        self.best_found_solution = self.current_solution

    def make_best_solution_current_solution(self) -> None:
        self.current_solution = self.best_found_solution

    def branching_lin_expression(self) -> gurobipy.LinExpr:
        """Return the LinExpr whose value is the hamming distance to the current solution."""
        return gurobipy.quicksum(
            1 - var if var_value > 0.5 else var
            for var, var_value in zip(
                self.assign_students_vars,
                self.current_solution.assign_students_var_values,
            )
        )

    def add_bounding_branching_constraint(self, rhs: int) -> None:
        """Only allow a hamming distance <= rhs to the current solution."""
        branching_constr_name = f"branching{next(self.counter)}"
        branching_constr = self.model.addConstr(
            self.branching_lin_expression() <= rhs,
            name=branching_constr_name,
        )
        self.branching_constraints.append(branching_constr)

    def pop_branching_constraints_stack(self) -> None:
        """Remove the branching constraint on top of the stack."""
        branching_constraint = self.branching_constraints.pop()
        self.model.remove(branching_constraint)

    def add_excluding_branching_constraint(self, rhs: int) -> None:
        """Only allow a hamming distance >= rhs + 1 to the current solution."""
        branching_constr_name = f"branching{next(self.counter)}"
        branching_constr = self.model.addConstr(
            self.branching_lin_expression() >= rhs + 1,
            name=branching_constr_name,
        )
        self.branching_constraints.append(branching_constr)

    def drop_all_branching_constraints(self) -> None:
        """Remove every constraint that was not part of the base model."""
        self.model.remove(self.branching_constraints)
        self.branching_constraints.clear()

    def add_shaking_constraints(self, k_cur: int, k_step: int) -> None:
        """Only allow k_cur <= hamming distance <= k_cur + k_step to the best solution"""
        lin_expr = self.branching_lin_expression()
        smaller_radius = self.model.addConstr(
            lin_expr >= k_cur,
        )
        bigger_radius = self.model.addConstr(
            lin_expr <= k_cur + k_step,
        )

        self.shake_constraints = smaller_radius, bigger_radius

    def remove_shaking_constraints(self) -> None:
        """Remove constraints for the shake once shake is over."""
        if self.shake_constraints is None:
            raise TypeError("Cannot remove shake constraints if None.")
        self.model.remove(self.shake_constraints)
        self.shake_constraints = None

    @classmethod
    def get(
        cls,
        initializer: Initializer,
    ) -> "LocalBrancher":
        """Return an instance of LocalBrancher after the initial optimization."""
        return cls(
            model_components=initializer.model_components,
            model=initializer.model,
            sol_reminder=initializer.current_solution,
            start_time=initializer.start_time,
            solution_summaries=initializer.solution_summaries,
        )

"""A class that contains a model which it reduces according to VNS rules."""

import functools
import random

import gurobipy

import utilities
from model_wrappers.model_wrapper import ModelWrapper
from model_wrappers.thin_wrappers import Initializer
from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from modeling.model_components import ModelComponents
from solving_utilities.assignment_fixing_data import AssignmentFixingData
from solving_utilities.group_shifter import GroupShifter
from solving_utilities.solution_reminder import SolutionReminder


class AssignmentFixer(ModelWrapper):
    """Contains a model further constrained for local branching."""

    def __init__(
        self,
        model_components: ModelComponents,
        model: gurobipy.Model,
        start_time: float,
        solution_summaries: list[dict[str, int | float | str]],
        config: Configuration,
        derived: DerivedModelingData,
        sol_reminder: SolutionReminder,
        fixing_data: AssignmentFixingData,
    ):
        super().__init__(model_components, model, start_time, solution_summaries, sol_reminder)
        self.config = config
        self.derived = derived
        self.current_sol_fixing_data = fixing_data
        self.best_sol_fixing_data = fixing_data

    def store_solution(self):
        self.current_solution = SolutionReminder(
            objective_value=self.objective_value,
            assign_students_var_values=utilities.var_values(self.assign_students_vars),
        )
        self.current_sol_fixing_data = AssignmentFixingData.get(
            config=self.config,
            derived=self.derived,
            variables=self.model_components.variables,
            lin_expressions=self.model_components.lin_expressions,
            model=self.model,
        )

    def make_current_solution_best_solution(self):
        self.best_found_solution = self.current_solution
        self.best_sol_fixing_data = self.current_sol_fixing_data

    def make_best_solution_current_solution(self):
        self.current_solution = self.best_found_solution
        self.current_sol_fixing_data = self.best_sol_fixing_data

    @functools.lru_cache(maxsize=128)
    def zones(self, num_zones: int) -> list[tuple[int, int]]:
        num_students = self.config.number_of_students
        floor_size = num_students // num_zones
        ceil_size = floor_size + 1
        num_ceil = num_students - (floor_size * num_zones)
        num_floor = num_zones - num_ceil
        sizes = random.sample([floor_size, ceil_size], counts=[num_floor, num_ceil], k=num_zones)
        boundaries: list[tuple[int, int]] = []
        current_idx = 0
        for size in sizes:
            boundaries.append((current_idx, current_idx + size))
            current_idx += size
        if current_idx != num_students:
            raise ValueError("Sizes do not add up to number of students.")
        return boundaries

    def _separate_assignments(
        self, zone_a: int, zone_b: int, num_zones: int, line_up: list[tuple[int, int, int]]
    ) -> tuple[list[tuple[int, int, int]], list[tuple[int, int, int]]]:
        start_a, end_a = (zones := self.zones(num_zones))[zone_a]
        start_b, end_b = zones[zone_b]
        return (
            line_up[start_a:end_a] + line_up[start_b:end_b],
            line_up[:start_a] + line_up[end_a:start_b] + line_up[end_b:],
        )

    def _separate_groups(
        self,
        free_assignments: list[tuple[int, int, int]],
        fixed_assignments: list[tuple[int, int, int]],
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        groups_of_free = set(
            (project_id, group_id)
            for project_id, group_id, _ in free_assignments
            if project_id != -1  # Must be real group
        )
        groups_of_fixed = set(
            (project_id, group_id)
            for project_id, group_id, _ in fixed_assignments
            if project_id != -1
        )
        return groups_of_free.difference(groups_of_fixed), groups_of_fixed

    def fix_rest(self, zone_a: int, zone_b: int, num_zones: int):
        free_assignments, fixed_assignments = self._separate_assignments(
            zone_a, zone_b, num_zones, self.current_sol_fixing_data.line_up_assignments
        )
        groups_only_free, groups_mixed = self._separate_groups(free_assignments, fixed_assignments)
        if groups_only_free:
            group_shifter = GroupShifter(
                groups_only_free=groups_only_free,
                groups_mixed=groups_mixed,
                line_up_assignments=self.current_sol_fixing_data.line_up_assignments,
                project_group_student_triples=self.derived.project_group_student_triples,
                assign_students_var_values=self.current_solution.assign_students_var_values,
            )
            start_values = group_shifter.adjusted_start_values
            free_assignments, fixed_assignments = self._separate_assignments(
                zone_a, zone_b, num_zones, group_shifter.adjusted_line_up_assignments
            )
            assignments = set(free_assignments + fixed_assignments)
        else:
            start_values = self.current_solution.assign_students_var_values
            assignments = self.current_sol_fixing_data.assignments

        self.model.setAttr("Start", self.assign_students_vars, start_values)

        free_student_ids = set(student_id for _, _, student_id in free_assignments)
        upper_bounds = [
            (
                1
                if student_id in free_student_ids
                or (project_id, group_id, student_id) in assignments
                else 0
            )
            for project_id, group_id, student_id in self.derived.project_group_student_triples
        ]
        self.model.setAttr("UB", self.assign_students_vars, upper_bounds)

    def delete_zoning_rules(self):
        self.zones.cache_clear()

    def force_k_worst_to_change(self, k: int):
        self.model.setAttr(
            "UB",
            self.assign_students_vars,
            [1] * len(self.assign_students_vars),
        )

        worst_k_assignments = self.current_sol_fixing_data.line_up_assignments[:k]
        variables = self.model_components.variables

        for project_id, group_id, student_id in worst_k_assignments:
            if project_id == -1:  # It is a pseudo_assignment
                var = variables.unassigned_students[student_id]
            else:
                var = variables.assign_students[project_id, group_id, student_id]
            var.UB = 0

        worst_k_student_ids = set(student_id for _, _, student_id in worst_k_assignments)
        start_values = [
            gurobipy.GRB.UNDEFINED if student_id in worst_k_student_ids else value
            for (_, _, student_id), value in zip(
                self.derived.project_group_student_triples,
                self.current_solution.assign_students_var_values,
            )
        ]

        self.model.setAttr("Start", self.assign_students_vars, start_values)

    def free_all_unassigned_vars(self):
        variables = list(self.model_components.variables.unassigned_students.values())
        self.model.setAttr("UB", variables, [1] * len(variables))

    @classmethod
    def get(cls, initializer: Initializer):
        return cls(
            config=initializer.config,
            derived=initializer.derived,
            model_components=initializer.model_components,
            model=initializer.model,
            sol_reminder=initializer.current_solution,
            fixing_data=initializer.fixing_data,
            start_time=initializer.start_time,
            solution_summaries=initializer.solution_summaries,
        )

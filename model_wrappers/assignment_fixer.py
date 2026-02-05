"""A class which offers commands that influence or decide which variables are fixed."""

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
    """Offers high-level commands that influence or decide which variables are fixed."""

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
        self._config = config
        self._derived = derived
        self._current_sol_fixing_data = fixing_data
        self._best_sol_fixing_data = fixing_data

    def store_solution(self) -> None:
        self._current_solution = SolutionReminder(
            objective_value=self.objective_value,
            assign_students_var_values=utilities.var_values(self._assign_students_vars),
        )
        self._current_sol_fixing_data = AssignmentFixingData.get(
            config=self._config,
            derived=self._derived,
            variables=self.model_components.variables,
            lin_expressions=self.model_components.lin_expressions,
            model=self._model,
        )

    def make_current_solution_best_solution(self) -> None:
        self._best_found_solution = self._current_solution
        self._best_sol_fixing_data = self._current_sol_fixing_data

    def make_best_solution_current_solution(self) -> None:
        self._current_solution = self._best_found_solution
        self._current_sol_fixing_data = self._best_sol_fixing_data

    @functools.lru_cache(maxsize=128)
    def _zones(self, num_zones: int) -> list[tuple[int, int]]:
        """Return the index boundaries of the zones within the ranked line up of assignments.

        E.g. 3 zones and 15 students: [(0, 5), (5, 10), (10, 15)]. This is compatible with
        list-splitting. If the number of students is not divisible by the number of zones, the
        sizes are randomly floor(num_students / zones) or ceil(num_students / zones) so that the
        zones stretch over the entire line up of assignments.
        """
        num_students = self._config.number_of_students
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
        """Return the assignments that will free and those that will be fixed separately.

        Args:
            zone_a, zone_b: A pair of zones in which the students will be free.
            num_zones: The overall number of zones. Influences the size of each zone which are
                roughly of equal size (see help(self.zones))
            line_up: Assignments in ascending order of individual assignment quality (See
                module individual_assignment_scorer)

        Returns:
            (assignments that are free, assignments that are fixed)
        """
        start_a, end_a = (zones := self._zones(num_zones))[zone_a]
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
        """Return the groups with only students which are free and those that are mixed separately.

        A group is mixed as soon as one student that is fixed is in it. This means it will have
        to remain open.

        Args:
            free_assignments: project id, group_id and student_id for every free student.
            fixed_assignments: The same for every student that is fixed.

        Returns:
            (groups with only free students, groups with at least one fixed_student in them)
        """
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

    def fix_rest(self, zone_a: int, zone_b: int, num_zones: int) -> None:
        """Fix all students which are not in the two zones.

        Also the start values of the assignment variables are set such that Gurobi starts at a
        solution equivalent to the current solution.

        The solution is only equivalent and not identical, since groups within projects may be
        shuffled.

        This beneficial because the MIP model demands that if a group with an index n  > 0 is open,
        that all groups with an index < n are also open. This is done to break symmetry.
        But if only one student in group n is fixed, the project has to have at least n + 1 groups.
        This can necessitate groups with an index < n and only free students in them to remain open
        even if a better solution would be possible when the group would be closed. Therefore it is
        ensured that groups which only have free students always have a higher group_id than those
        that have at least one fixed student.
        """
        free_assignments, fixed_assignments = self._separate_assignments(
            zone_a, zone_b, num_zones, self._current_sol_fixing_data.line_up_assignments
        )
        groups_only_free, groups_mixed = self._separate_groups(free_assignments, fixed_assignments)
        if groups_only_free:
            group_shifter = GroupShifter(
                groups_only_free=groups_only_free,
                groups_mixed=groups_mixed,
                line_up_assignments=self._current_sol_fixing_data.line_up_assignments,
                project_group_student_triples=self._derived.project_group_student_triples,
                assign_students_var_values=self._current_solution.assign_students_var_values,
            )
            start_values = group_shifter.adjusted_start_values
            free_assignments, fixed_assignments = self._separate_assignments(
                zone_a, zone_b, num_zones, group_shifter.adjusted_line_up_assignments
            )
            assignments = set(free_assignments + fixed_assignments)
        else:
            start_values = self._current_solution.assign_students_var_values
            assignments = self._current_sol_fixing_data.assignments

        self._model.setAttr("Start", self._assign_students_vars, start_values)

        free_student_ids = set(student_id for _, _, student_id in free_assignments)
        upper_bounds = [
            (
                1
                if student_id in free_student_ids
                or (project_id, group_id, student_id) in assignments
                else 0
            )
            for project_id, group_id, student_id in self._derived.project_group_student_triples
        ]
        self._model.setAttr("UB", self._assign_students_vars, upper_bounds)

    def delete_zoning_rules(self) -> None:
        """Delete the pairs of boundary indexes which delimit the zones.

        These boundary indexes are in random if the number of students is not divisible by the
        number of zones (see help(self.zones))
        """
        self._zones.cache_clear()

    def force_k_worst_to_change(self, k: int) -> None:
        """Force the k students with the worst individual assignment score to change assignment.

        This is a preparatory step for the optimization during the shake. It consists of the
        following temporary changes to the optimization problem.

        1. All students which are not part of the worst k are free to move
        2. Those that are in the worst k are only prohibited from keeping their current assignment
            or to stay unassigned
        3. For all students which are not in the worst k the start assignment is their current
            assignment
        """
        self._model.setAttr(
            "UB",
            self._assign_students_vars,
            [1] * len(self._assign_students_vars),
        )

        worst_k_assignments = self._current_sol_fixing_data.line_up_assignments[:k]
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
                self._derived.project_group_student_triples,
                self._current_solution.assign_students_var_values,
            )
        ]

        self._model.setAttr("Start", self._assign_students_vars, start_values)

    def free_all_unassigned_vars(self) -> None:
        """Free all the variables that specify whether a student is unassigned or not.

        Necessary only after shaking since they are not fixed elsewhere.
        """
        variables = list(self.model_components.variables.unassigned_students.values())
        self._model.setAttr("UB", variables, [1] * len(variables))

    @classmethod
    def get(cls, initializer: Initializer) -> "AssignmentFixer":
        """Return an instance of AssignmentFixer after the initial optimization."""
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

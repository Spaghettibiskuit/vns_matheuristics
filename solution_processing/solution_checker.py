"""A class that checks whether a solution is valid and the objective value calculated correctly."""

import functools

from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from modeling.model_components import LinExpressions
from solution_processing.solution_info_retriever import SolutionInformationRetriever
from utilities import gurobi_round


class SolutionChecker:
    """Checks whether the solution is valid and the objective value calculated correctly."""

    def __init__(
        self,
        config: Configuration,
        derived: DerivedModelingData,
        lin_expressions: LinExpressions,
        retriever: SolutionInformationRetriever,
    ):
        self.config = config
        self.derived = derived
        self.lin_expressions = lin_expressions
        self.retriever = retriever

    @functools.cached_property
    def _all_students_either_assigned_once_or_unassigned(self) -> bool:
        unassigned_students = self.retriever.unassigned_students
        assigned_students = [student_id for _, _, student_id in self.retriever.assignments]
        return sorted(unassigned_students + assigned_students) == list(self.derived.student_ids)

    @functools.cached_property
    def _groups_opened_if_and_only_if_students_inside(self) -> bool:
        derived_open_groups = set(
            (project_id, group_id) for project_id, group_id, _ in self.retriever.assignments
        )
        return sorted(derived_open_groups) == self.retriever.established_groups

    @functools.cached_property
    def _all_group_sizes_within_bounds(self) -> bool:
        min_group_size = self.config.projects_info["min_group_size"]
        max_group_size = self.config.projects_info["max_group_size"]
        return all(
            min_group_size[project_id]
            <= len(self.retriever.students_in_group[project_id, group_id])
            <= max_group_size[project_id]
            for project_id, group_id in self.retriever.established_groups
        )

    @functools.cached_property
    def _no_project_too_many_established_groups(self) -> bool:
        max_num_groups = self.config.projects_info["max#groups"]
        return all(
            len(self.retriever.groups_in_project[project_id]) <= max_num_groups[project_id]
            for project_id in self.derived.project_ids
        )

    @functools.cached_property
    def _all_projects_only_consecutive_group_ids(self) -> bool:
        return all(
            sorted(groups := self.retriever.groups_in_project[project_id])
            == list(range(len(groups)))
            for project_id in self.derived.project_ids
        )

    @functools.cached_property
    def _is_valid(self) -> bool:
        return (
            self._all_students_either_assigned_once_or_unassigned
            and self._groups_opened_if_and_only_if_students_inside
            and self._all_group_sizes_within_bounds
            and self._no_project_too_many_established_groups
            and self._all_projects_only_consecutive_group_ids
        )

    @functools.cached_property
    def _sum_realized_project_preferences(self) -> int | float:
        project_preferences = self.derived.project_preferences
        return sum(
            project_preferences[student_id, project_id]
            for project_id, _, student_id in self.retriever.assignments
        )

    @functools.cached_property
    def _sum_reward_mutual(self) -> int | float:
        return len(self.retriever.mutual_pairs) * self.config.reward_mutual_pair

    @functools.cached_property
    def _sum_penalties_unassigned(self) -> int | float:
        return len(self.retriever.unassigned_students) * self.config.penalty_unassigned

    @functools.cached_property
    def _sum_penalties_surplus_groups(self) -> int | float:
        desired_num_of_groups = self.config.projects_info["desired#groups"]
        penalty_per_excess_group = self.config.projects_info["pen_groups"]
        return sum(
            max(
                0,
                len(self.retriever.groups_in_project[project_id])
                - desired_num_of_groups[project_id],
            )
            * penalty_per_excess_group[project_id]
            for project_id in self.derived.project_ids
        )

    @functools.cached_property
    def _sum_penalties_group_size(self) -> int | float:
        ideal_group_size = self.config.projects_info["ideal_group_size"]
        penalty_deviation = self.config.projects_info["pen_size"]
        return sum(
            abs(
                len(self.retriever.students_in_group[project_id, group_id])
                - ideal_group_size[project_id]
            )
            * penalty_deviation[project_id]
            for project_id, group_id in self.retriever.established_groups
        )

    @functools.cached_property
    def _sum_realized_project_preferences_correct(self) -> bool:
        return self._sum_realized_project_preferences == gurobi_round(
            self.lin_expressions.sum_realized_project_preferences.getValue()
        )

    @functools.cached_property
    def _sum_reward_mutual_correct(self) -> bool:
        return self._sum_reward_mutual == gurobi_round(
            self.lin_expressions.sum_reward_mutual.getValue()
        )

    @functools.cached_property
    def _sum_penalties_unassigned_correct(self) -> bool:
        return self._sum_penalties_unassigned == gurobi_round(
            self.lin_expressions.sum_penalties_unassigned.getValue()
        )

    @functools.cached_property
    def _sum_penalties_surplus_groups_correct(self) -> bool:
        return self._sum_penalties_surplus_groups == gurobi_round(
            self.lin_expressions.sum_penalties_surplus_groups.getValue()
        )

    @functools.cached_property
    def _sum_penalties_group_size_correct(self) -> bool:
        return self._sum_penalties_group_size == gurobi_round(
            self.lin_expressions.sum_penalties_group_size.getValue()
        )

    @functools.cached_property
    def _objective_value_calculated_correctly(self) -> bool:
        return (
            self._sum_realized_project_preferences_correct
            and self._sum_reward_mutual_correct
            and self._sum_penalties_unassigned_correct
            and self._sum_penalties_surplus_groups_correct
            and self._sum_penalties_group_size_correct
        )

    @functools.cached_property
    def is_correct(self) -> bool:
        """Return whether the solution is valid and the objective value calculated correctly."""
        return self._is_valid and self._objective_value_calculated_correctly

"""A class that retrieves information regarding the solution within a Gurobi model."""

import functools
import itertools

from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from modeling.model_components import Variables


class SolutionInformationRetriever:
    """Retrieves information regarding the solution within a Gurobi model."""

    def __init__(
        self,
        config: Configuration,
        derived: DerivedModelingData,
        variables: Variables,
    ):
        self.config = config
        self.derived = derived
        self.variables = variables

    @functools.cached_property
    def assignments(self) -> list[tuple[int, int, int]]:
        return [k for k, v in self.variables.assign_students.items() if v.X > 0.5]

    @functools.cached_property
    def established_groups(self) -> list[tuple[int, int]]:
        return [k for k, v in self.variables.establish_groups.items() if v.X > 0.5]

    @functools.cached_property
    def unassigned_students(self) -> list[int]:
        return [k for k, v in self.variables.unassigned_students.items() if v.X > 0.5]

    @functools.cached_property
    def students_in_group(self) -> dict[tuple[int, int], list[int]]:
        in_group: dict[tuple[int, int], list[int]] = {
            (project_id, group_id): []
            for project_id in self.derived.project_ids
            for group_id in range(max(self.config.projects_info["max#groups"]))
        }
        for project_id, group_id, student_id in self.assignments:
            in_group[project_id, group_id].append(student_id)
        return in_group

    @functools.cached_property
    def groups_in_project(self) -> dict[int, list[int]]:
        in_project: dict[int, list[int]] = {project: [] for project in self.derived.project_ids}
        for project_id, group_id in self.established_groups:
            in_project[project_id].append(group_id)
        return in_project

    @functools.cached_property
    def students_in_project(self) -> dict[int, list[int]]:
        in_project: dict[int, list[int]] = {project: [] for project in self.derived.project_ids}
        for project_id, _, student_id in self.assignments:
            in_project[project_id].append(student_id)
        return in_project

    @functools.lru_cache(maxsize=1_280)
    def pref_vals_students_in_group(self, project_id: int, group_id: int) -> dict[int, int]:
        project_preferences = self.derived.project_preferences
        return {
            student_id: project_preferences[student_id, project_id]
            for student_id in self.students_in_group[project_id, group_id]
        }

    @functools.lru_cache(maxsize=1_280)
    def mutual_pairs_in_group(self, project_id: int, group_id: int) -> list[tuple[int, int]]:
        mutual_pairs = self.derived.mutual_pairs_items
        return [
            pair
            for pair in itertools.combinations(self.students_in_group[project_id, group_id], 2)
            if pair in mutual_pairs
        ]

    @functools.cached_property
    def mutual_pairs(self) -> list[tuple[int, int]]:
        return [
            pair
            for group in self.derived.project_group_pairs
            for pair in self.mutual_pairs_in_group(*group)
        ]

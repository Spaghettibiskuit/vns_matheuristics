"""A class that retrieves information regarding the solution within a Gurobi model."""

import functools
import itertools

from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from modeling.model_components import Variables


class SolutionInformationRetriever:
    """Retrieves information regarding the solution within a Gurobi model.

    Attributes:
        config: Contains all all specifications that define an instance of the SSPAGDP.
        derived: Iterables and hash-table backed containers that derive from the configuration.
    """

    def __init__(
        self,
        config: Configuration,
        derived: DerivedModelingData,
        variables: Variables,
    ):
        self.config = config
        self.derived = derived
        self._variables = variables

    @functools.cached_property
    def assignments(self) -> list[tuple[int, int, int]]:
        """All assignments specified with (project_id, group_id, student_id)."""
        return [k for k, v in self._variables.assign_students.items() if v.X > 0.5]

    @functools.cached_property
    def established_groups(self) -> list[tuple[int, int]]:
        """All groups that are populated specified with (project_id, group_id)."""
        return [k for k, v in self._variables.establish_groups.items() if v.X > 0.5]

    @functools.cached_property
    def unassigned_students(self) -> list[int]:
        """The IDs of all students not assigned to any group."""
        return [k for k, v in self._variables.unassigned_students.items() if v.X > 0.5]

    @functools.cached_property
    def students_in_group(self) -> dict[tuple[int, int], list[int]]:
        """The IDs of students in a group for any group in all projects.

        (project_id, group_id) -> IDs of students assigned to the group
        """
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
        """The IDs of groups that are populated in a project for all projects.

        project_id -> IDs of groups in the project that are populated.
        """
        in_project: dict[int, list[int]] = {project: [] for project in self.derived.project_ids}
        for project_id, group_id in self.established_groups:
            in_project[project_id].append(group_id)
        return in_project

    @functools.cached_property
    def students_in_project(self) -> dict[int, list[int]]:
        """The IDs of the students that are in any group for all projects.

        project_id -> IDs of students in any group in the project.
        """
        in_project: dict[int, list[int]] = {project: [] for project in self.derived.project_ids}
        for project_id, _, student_id in self.assignments:
            in_project[project_id].append(student_id)
        return in_project

    @functools.lru_cache(maxsize=1_280)
    def pref_vals_students_in_group(self, project_id: int, group_id: int) -> dict[int, int]:
        """The preference value of the students in a group for the project the group is in.

        student_id -> Preference value for the project the group is part of.
        """
        project_preferences = self.derived.project_preferences
        return {
            student_id: project_preferences[student_id, project_id]
            for student_id in self.students_in_group[project_id, group_id]
        }

    @functools.lru_cache(maxsize=1_280)
    def mutual_pairs_in_group(self, project_id: int, group_id: int) -> list[tuple[int, int]]:
        """Pairs of students that want to work together in a group in a specific project."""
        mutual_pairs = self.derived.mutual_pairs_items
        return [
            pair
            for pair in itertools.combinations(self.students_in_group[project_id, group_id], 2)
            if pair in mutual_pairs
        ]

    @functools.cached_property
    def mutual_pairs(self) -> list[tuple[int, int]]:
        """All pairs of students that want to work together that are assigned to the same group."""
        return [
            pair
            for group in self.derived.project_group_pairs
            for pair in self.mutual_pairs_in_group(*group)
        ]

"""A class with iterables and hash-table backed containers that derive from the configuration."""

from dataclasses import dataclass

from modeling.configuration import Configuration


@dataclass(frozen=True)
class DerivedModelingData:
    """Iterables and hash-table backed containers that derive from the configuration.

    The configuration is an instance of modeling.configuration.Configuration.

    Attributes:
        project_ids: The range of project IDs.
        student_ids: The range of student IDs.
        group_ids: The range of potential group IDs for every project.
        project_group_pairs: All potential groups specified with tuples of (project_id, group_id).
            The tuples are sorted.
        project_group_student_triples: All possible assignments of students to groups specified
            with (project_id, group_id, student). The tuples are sorted.
        mutual_pairs_ordered: All tuples of (student_id_a, student_id_b) where both students want
            to work with each other. Always student_id_a < student_id_b.
        mutual_pairs_items: Tuples as above but in a set for faster lookup during optimization.
        project_preferences: Preference value of every student for each project.
            Each key is tuple of (student_id, project_id).
    """

    project_ids: range
    student_ids: range
    group_ids: dict[int, range]
    project_group_pairs: tuple[tuple[int, int], ...]
    project_group_student_triples: tuple[tuple[int, int, int], ...]
    mutual_pairs_ordered: tuple[tuple[int, int], ...]
    mutual_pairs_items: frozenset[tuple[int, int]]
    project_preferences: dict[tuple[int, int], int]

    @classmethod
    def get(cls, config: Configuration):
        """Alternative initializer for a frozen dataclass."""
        project_ids = range(len(config.projects_info))
        student_ids = range(len(config.students_info))
        group_ids = {
            project_id: range(max_num_groups)
            for project_id, max_num_groups in enumerate(config.projects_info["max#groups"])
        }
        project_group_pairs = tuple(
            (project_id, group_id)
            for project_id, project_group_ids in group_ids.items()
            for group_id in project_group_ids
        )
        project_group_student_triples = tuple(
            (project_id, group_id, student_id)
            for project_id, group_id in project_group_pairs
            for student_id in student_ids
        )
        mutual_pairs_ordered = tuple(
            (student_id, partner_id)
            for student_id, partner_ids in enumerate(config.students_info["fav_partners"])
            for partner_id in partner_ids
            if partner_id > student_id
            and student_id in config.students_info["fav_partners"][partner_id]
        )
        mutual_pairs_items = frozenset(mutual_pairs_ordered)
        project_preferences = {
            (student_id, project_id): preference_value
            for student_id, preference_values in enumerate(config.students_info["project_prefs"])
            for project_id, preference_value in enumerate(preference_values)
        }
        return cls(
            project_ids=project_ids,
            student_ids=student_ids,
            group_ids=group_ids,
            project_group_pairs=project_group_pairs,
            project_group_student_triples=project_group_student_triples,
            mutual_pairs_ordered=mutual_pairs_ordered,
            mutual_pairs_items=mutual_pairs_items,
            project_preferences=project_preferences,
        )

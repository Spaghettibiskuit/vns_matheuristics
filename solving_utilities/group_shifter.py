import functools
import itertools


class GroupShifter:

    def __init__(
        self,
        groups_only_free: set[tuple[int, int]],
        groups_mixed: set[tuple[int, int]],
        line_up_assignments: list[tuple[int, int, int]],
        project_group_student_triples: tuple[tuple[int, int, int], ...],
        assign_students_var_values: tuple[int | float, ...],
    ):
        self._groups_only_free = groups_only_free
        self._groups_mixed = groups_mixed
        self._original_line_up_assignments = line_up_assignments
        self._project_group_student_triples = project_group_student_triples
        self._assign_students_var_values = assign_students_var_values

    @functools.cached_property
    def _shifted_groups(self) -> dict[tuple[int, int], tuple[int, int]]:
        all_groups = self._groups_only_free.union(self._groups_mixed)
        if len(all_groups) != len(self._groups_only_free) + len(self._groups_mixed):
            raise ValueError()

        affected_projects = set(project_id for project_id, _ in self._groups_only_free)
        only_free_groups: dict[int, list[int]] = {
            project_id: [] for project_id in affected_projects
        }
        mixed_affected_groups: dict[int, list[int]] = {
            project_id: [] for project_id in affected_projects
        }

        for project_id, group_id in all_groups:
            if project_id in affected_projects:
                if (project_id, group_id) in self._groups_only_free:
                    only_free_groups[project_id].append(group_id)
                else:
                    mixed_affected_groups[project_id].append(group_id)

        return {
            (project_id, group_id): (project_id, new_group_id)
            for (project_id, mixed_affected_groups), (_, only_free_affected_groups) in zip(
                sorted(mixed_affected_groups.items()), sorted(only_free_groups.items())
            )
            for group_id, new_group_id in zip(
                mixed_affected_groups + only_free_affected_groups,
                itertools.count(),
            )
        }

    @property
    def adjusted_line_up_assignments(self) -> list[tuple[int, int, int]]:
        shifted_groups = self._shifted_groups
        return [
            (
                (*shifted_group, student_id)
                if (shifted_group := shifted_groups.get((proj_id, group_id))) is not None
                else (proj_id, group_id, student_id)
            )
            for proj_id, group_id, student_id in self._original_line_up_assignments
        ]

    @property
    def adjusted_start_values(self) -> list[int | float]:
        shifted_groups = self._shifted_groups
        start_values = dict(
            zip(
                self._project_group_student_triples,
                self._assign_students_var_values,
            )
        )
        for project_id, group_id, student_id in self._original_line_up_assignments:
            if (new_group := shifted_groups.get((project_id, group_id))) is not None:
                old = (project_id, group_id, student_id)
                new = (*new_group, student_id)
                start_values[old], start_values[new] = start_values[new], start_values[old]

        return list(start_values.values())

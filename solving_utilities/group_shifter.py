import functools


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

    @property
    def _shifted_groups(self) -> dict[tuple[int, int], tuple[int, int]]:
        affected_projects = set(project_id for project_id, _ in self._groups_only_free)
        only_free_groups: dict[int, list[int]] = {
            project_id: [] for project_id in affected_projects
        }
        mixed_affected_groups: dict[int, list[int]] = {
            project_id: [] for project_id in affected_projects
        }
        for project_id, group_id in self._groups_only_free:
            only_free_groups[project_id].append(group_id)

        for project_id, group_id in self._groups_mixed:
            if project_id in affected_projects:
                mixed_affected_groups[project_id].append(group_id)

        return {
            (project_id, group_id): (project_id, new_group_id)
            for (project_id, mixed_groups), (_, free_groups) in zip(
                sorted(mixed_affected_groups.items()), sorted(only_free_groups.items())
            )
            for new_group_id, group_id in enumerate(mixed_groups + free_groups)
        }

    @functools.cached_property
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
        start_values = dict(
            zip(
                self._project_group_student_triples,
                self._assign_students_var_values,
            )
        )
        for old, new in zip(self._original_line_up_assignments, self.adjusted_line_up_assignments):
            start_values[old], start_values[new] = start_values[new], start_values[old]

        return list(start_values.values())

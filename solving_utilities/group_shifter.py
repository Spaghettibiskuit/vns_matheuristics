import functools


class GroupShifter:
    """Generates data to let Gurobi start at an equivalent, more convenient solution.

    More convenient because group indexes are such that the group indexes of those groups which
    only have free students are always greater than the group index of any group in the same
    project in which there is at least one fixed student. This way the project has to retain only
    those groups populated in which at least one student is fixed.

    Equivalent, because only group indexes are switched. No group has changed members or project.
    """

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
        """New group indexes where those of groups with only free students are always greater.*

        *Than that of any group in the same project in which there is at least one fixed student.

        The mapping is from (project_id, old_group_id) to (project_id, new_group_id).
        """
        only_free_groups: dict[int, list[int]] = {}
        for project_id, group_id in self._groups_only_free:
            only_free_groups.setdefault(project_id, []).append(group_id)

        mixed_affected_groups: dict[int, list[int]] = {
            project_id: [] for project_id in only_free_groups
        }
        for project_id, group_id in self._groups_mixed:
            if (group_ids := mixed_affected_groups.get(project_id)) is not None:
                group_ids.append(group_id)

        return {
            (project_id, group_id): (project_id, new_group_id)
            for (project_id, free_groups), mixed_groups in zip(
                only_free_groups.items(), mixed_affected_groups.values()
            )
            for new_group_id, group_id in enumerate(mixed_groups + free_groups)
        }

    @functools.cached_property
    def adjusted_line_up_assignments(self) -> list[tuple[int, int, int]]:
        """The line up by ascending individual assignment score with new group indexes.

        The group indexes are such that the group indexes of those groups which only have free
        students are always greater than the group index of any group in the same project in which
        there is at least one fixed student.
        """
        shifted_groups = self._shifted_groups
        return [
            (
                (*shifted_group, student_id)
                if (shifted_group := shifted_groups.get((project_id, group_id))) is not None
                else (project_id, group_id, student_id)
            )
            for project_id, group_id, student_id in self._original_line_up_assignments
        ]

    @property
    def adjusted_start_values(self) -> tuple[int | float, ...]:
        """Start values to the assignment variables for an equivalent solution.

        It is equivalent not equal since groups indexes within each project may have been switched.
        """
        start_values = dict(
            zip(
                self._project_group_student_triples,
                self._assign_students_var_values,
            )
        )
        for old, new in zip(self._original_line_up_assignments, self.adjusted_line_up_assignments):
            start_values[old], start_values[new] = start_values[new], start_values[old]

        return tuple(start_values.values())

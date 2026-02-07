"""A class that allows to view summary statistics of the best solution."""

import functools
import statistics
import typing

import pandas

from solution_processing.solution_info_retriever import SolutionInformationRetriever


class SolutionViewer:
    """Allows to view summary statistics of the best solution."""

    def __init__(self, retriever: SolutionInformationRetriever):
        self._derived = retriever.derived
        self._retriever = retriever

    @functools.cached_property
    def solution_summary(self) -> pandas.DataFrame:
        """Summary stats about the solution quality for all projects.

        The row index is not necessarily the project ID. If no group is populated in the project no
        summary statistics are shown for it.

        For every project the following is stated:
        ID: The ID of the project.
        #students: The number of students in the project.
        #groups: The number of groups in the project.
        max_size: The maximum number of students in a group in the project.
        min_size: The minimum...
        mean_size: The mean...
        max_pref: The maximum preference for the project among the students in the project.
        min_pref: The minimum...
        mean_pref: The mean...
        #mutual_pairs: The number of pairs of students that want to work together that are in the
            same group summed over all groups in the project.
        """
        open_projects = {
            project_id: self.summary_table_project(project_id)
            for project_id in self._derived.project_ids
            if self._retriever.groups_in_project[project_id]
        }
        summary_tables = open_projects.values()
        group_quantities = [len(summary_table) for summary_table in summary_tables]
        student_quantities = [sum(summary_table["#students"]) for summary_table in summary_tables]

        projects_summary_stats: dict[str, typing.Any] = {
            "ID": open_projects.keys(),
            "#groups": group_quantities,
            "max_size": [max(summary_table["#students"]) for summary_table in summary_tables],
            "min_size": [min(summary_table["#students"]) for summary_table in summary_tables],
            "mean_size": [
                num_students / num_groups
                for num_students, num_groups in zip(student_quantities, group_quantities)
            ],
            "max_pref": [max(summary_table["max_pref"]) for summary_table in summary_tables],
            "min_pref": [min(summary_table["min_pref"]) for summary_table in summary_tables],
            "mean_pref": [
                (summary_table["#students"] * summary_table["mean_pref"]).sum() / num_students
                for num_students, summary_table in zip(student_quantities, summary_tables)
            ],
            "#mutual_pairs": [
                sum(summary_table["#mutual_pairs"]) for summary_table in summary_tables
            ],
        }

        return pandas.DataFrame(projects_summary_stats)

    @functools.lru_cache(maxsize=128)
    def summary_table_project(self, project_id: int) -> pandas.DataFrame:
        """Summary stats about the solution quality for a project.

        The row index is the group ID. For every group the following is stated:
        #students: The number of students in the group.
        max_pref: The maximum preference for the project among the students in the group.
        min_pref: The minimum...
        mean_pref: The mean...
        #mutual_pairs: The number of pairs of students that want to work together.
        """
        pref_vals_in_groups = [
            list(self._retriever.pref_vals_students_in_group(project_id, group_id).values())
            for group_id in self._retriever.groups_in_project[project_id]
        ]
        summaries: dict[str, list[int | float]] = {
            "#students": [
                len(self._retriever.students_in_group[project_id, group_id])
                for group_id in self._retriever.groups_in_project[project_id]
            ],
            "max_pref": [max(pref_vals) for pref_vals in pref_vals_in_groups],
            "min_pref": [min(pref_vals) for pref_vals in pref_vals_in_groups],
            "mean_pref": [statistics.mean(pref_vals) for pref_vals in pref_vals_in_groups],
            "#mutual_pairs": [
                len(self._retriever.mutual_pairs_in_group(project_id, group_id))
                for group_id in self._retriever.groups_in_project[project_id]
            ],
        }

        return pandas.DataFrame(summaries)

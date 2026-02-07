"""Class that allows to view and save solution and has classes to assess solution as attributes.

It is returned at the end of both heuristic algorithms and after solving with Gurobi alone.
"""

from dataclasses import fields
from functools import cached_property
from pathlib import Path

import pandas

from model_wrappers.model_wrapper import ModelWrapper
from model_wrappers.thin_wrappers import GurobiAloneWrapper
from solution_processing.solution_checker import SolutionChecker
from solution_processing.solution_info_retriever import SolutionInformationRetriever
from solution_processing.solution_viewer import SolutionViewer


class SolutionAccess:
    """Allows to view and save solution and has classes to assess solution as attributes.

    Is returned at the end of both heuristic algorithms and after solving with Gurobi alone.
    """

    def __init__(
        self,
        model: ModelWrapper | GurobiAloneWrapper,
        retriever: SolutionInformationRetriever,
        viewer: SolutionViewer,
        checker: SolutionChecker,
    ):
        self.config = retriever.config
        self.derived = retriever.derived
        self.model = model
        self.retriever = retriever
        self.viewer = viewer
        self.checker = checker

    @cached_property
    def solution_table(self) -> pandas.DataFrame:
        """Rows are project IDs, columns group IDs, lists of student IDs are in the cells.

        Those student IDs are of the students that are in that group in this specific project.
        """
        max_group_id = max(self.config.projects_info["max#groups"])
        students_in_groups = {
            group_id: [
                self.retriever.students_in_group.get((project_id, group_id), [])
                for project_id in self.derived.project_ids
            ]
            for group_id in range(max_group_id)
        }
        return pandas.DataFrame(students_in_groups)

    def save_as_csv(self, filename: str, suffix: str = "csv") -> None:
        """Save solution_table as a csv with info on how the objective was reached as comments.

        These comments that inform how the objective was reached include:
        - The objective value itself
        - The penalty per unassigned student
        - The reward per materialized mutual pair
        - The values of the linear expressions which make up the objective
        - The mutual pairs where both work together (as pairs of IDs)
        - The IDs of the students that are not assigned to any group
        """
        target_folder = Path("solutions") / "custom"
        path = target_folder / f"{filename}.{suffix}"
        if path.exists():
            raise ValueError("Path already exists.")

        target_folder.mkdir(parents=True, exist_ok=True)

        top_comments = [
            f"# Objective: {self.model.objective_value}",
            f"# Penalty per unassigned student: {self.config.penalty_unassigned}",
            f"# Reward per materialized mutual pair: {self.config.reward_mutual_pair}",
        ]

        descriptors = [
            "Sum of the realized project preferences",
            "Sum of rewards for materialized mutual pairs",
            "Sum of the penalties for leaving students unassigned",
            "Sum of penalties for surplus groups",
            "Sum of penalties for not ideal group sizes",
        ]

        lin_expr_values = [
            getattr(self.model.model_components.lin_expressions, field.name).getValue()
            for field in fields(self.model.model_components.lin_expressions)
        ]

        middle_comments = [
            f"# {descriptor}: {value:.1f}"
            for descriptor, value in zip(descriptors, lin_expr_values)
        ]

        bottom_comments = [
            f"# Mutual pairs where both work together: {str(self.retriever.mutual_pairs)[1:-1]}",
            f"# Unassigned students: {str(self.retriever.unassigned_students)[1:-1]}",
        ]
        comments = top_comments + middle_comments + bottom_comments

        path.write_text(
            "\n".join(comments + [self.solution_table.to_csv()]),
            encoding="utf-8",
        )

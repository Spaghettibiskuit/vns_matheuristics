"""A class with data that is the basis for which assignments are fixed when."""

import random
from dataclasses import dataclass

import gurobipy

from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from modeling.model_components import LinExpressions, Variables
from solving_utilities.individual_assignment_scorer import IndividualAssignmentScorer


@dataclass(frozen=True)
class AssignmentFixingData:
    """Data that is the basis for which assignments are fixed when.

    Attributes:
        assignments: The current assignments of the form (project_id, group_id, student_id)
        line_up_assignments: The assignments ranked in ascending order by their individual
            assignment score. For more on the individual assignment score see
            solving_utilities.individual_assignment_scorer. If there are unassigned students they
            are randomly positioned among this line_up. Those pseudo-assignments are of the form
            (project_id=-1, group_id=-1, student_id=foo).
    """

    assignments: set[tuple[int, int, int]]
    line_up_assignments: list[tuple[int, int, int]]

    @classmethod
    def get(
        cls,
        config: Configuration,
        derived: DerivedModelingData,
        variables: Variables,
        lin_expressions: LinExpressions,
        model: gurobipy.Model,
    ):
        """Alternative initializer for a frozen dataclass."""
        scores = IndividualAssignmentScorer(
            config, derived, variables, lin_expressions
        ).assignment_scores
        ranked_assignments = sorted(scores.keys(), key=lambda k: scores[k])
        unassigned_ids = [k for k, v in variables.unassigned_students.items() if v.X > 0.5]
        derived_obj_val = sum(scores.values()) - len(unassigned_ids) * config.penalty_unassigned

        if abs(derived_obj_val - model.ObjVal) > 1e-1:
            raise ValueError(f"derived {derived_obj_val} is not real {model.ObjVal}")

        if unassigned_ids:
            line_up_assignments = _fixing_line_up_assignments(
                config, derived, ranked_assignments, unassigned_ids
            )
        else:
            line_up_assignments = ranked_assignments

        return cls(
            assignments=set(ranked_assignments),
            line_up_assignments=line_up_assignments,
        )


def _fixing_line_up_assignments(
    config: Configuration,
    derived: DerivedModelingData,
    ranked_assignments: list[tuple[int, int, int]],
    unassigned_ids: list[int],
):

    pseudo_assignments = ((-1, -1, student_id) for student_id in unassigned_ids)
    actual_assignments = iter(ranked_assignments)

    positions = set(random.sample(derived.student_ids, k=len(unassigned_ids)))

    line_up: list[tuple[int, int, int]] = []

    for i in range(config.number_of_students):
        if i in positions:
            line_up.append(next(pseudo_assignments))
        else:
            line_up.append(next(actual_assignments))

    return line_up

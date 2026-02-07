"""A class to build the base model for an instance of the SSPAGDP and get the components of it.

Usage example:
model_components, model = BaseModelBuilder(config, derived).get_base_model()
"""

from typing import cast

import gurobipy as gp
from gurobipy import GRB

from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from modeling.model_components import (
    InitialConstraints,
    LinExpressions,
    ModelComponents,
    Variables,
)


class BaseModelBuilder:
    """Build the base model for an instance of the SSPAGDP and get the components of it."""

    def __init__(self, config: Configuration, derived: DerivedModelingData):
        self._penalty_unassigned = config.penalty_unassigned
        self._reward_mutual_pair = config.reward_mutual_pair
        self._projects_info = config.projects_info
        self._students_info = config.students_info
        self._project_ids = derived.project_ids
        self._student_ids = derived.student_ids
        self._group_ids = derived.group_ids
        self._project_group_pairs = derived.project_group_pairs
        self._project_group_student_triples = derived.project_group_student_triples
        self._mutual_pairs = derived.mutual_pairs_ordered
        self._project_preferences = derived.project_preferences
        self._model = gp.Model()

    def get_base_model(self) -> tuple[ModelComponents, gp.Model]:
        """Return the model and references to its variables, linear expressions and constraints.

        The variables and constraints can be by retrieved via tuples of indexes e.g.
        (project_id, group_id, student_id) since they are instances of gurobipy.tupledict.
        """
        variables = self._add_variables()
        lin_expressions = self._construct_linear_expressions(variables=variables)
        self._set_objective(lin_expressions=lin_expressions)
        initial_constraints = self._add_constraints(variables=variables)
        return ModelComponents(variables, lin_expressions, initial_constraints), self._model

    def _add_variables(self) -> Variables:
        assign_students = self._model.addVars(
            self._project_group_student_triples,
            vtype=GRB.BINARY,
            name="assign_students",
        )
        establish_groups = self._model.addVars(
            self._project_group_pairs, vtype=GRB.BINARY, name="establish_groups"
        )
        mutual_unrealized = self._model.addVars(
            self._mutual_pairs, vtype=GRB.BINARY, name="mutual_unrealized"
        )
        unassigned_students = self._model.addVars(self._student_ids, name="unassigned_students")

        group_size_surplus = self._model.addVars(
            self._project_group_pairs, name="group_size_surplus"
        )

        group_size_deficit = self._model.addVars(
            self._project_group_pairs, name="group_size_deficit"
        )
        return Variables(
            assign_students=cast(gp.tupledict[tuple[int, int, int], gp.Var], assign_students),
            establish_groups=cast(gp.tupledict[tuple[int, int], gp.Var], establish_groups),
            mutual_unrealized=cast(gp.tupledict[tuple[int, int], gp.Var], mutual_unrealized),
            unassigned_students=cast(gp.tupledict[int, gp.Var], unassigned_students),
            group_size_surplus=cast(gp.tupledict[tuple[int, int], gp.Var], group_size_surplus),
            group_size_deficit=cast(gp.tupledict[tuple[int, int], gp.Var], group_size_deficit),
        )

    def _construct_linear_expressions(self, variables: Variables) -> LinExpressions:
        sum_realized_project_preferences = gp.quicksum(
            self._project_preferences[student_id, project_id] * var
            for (project_id, _, student_id), var in variables.assign_students.items()
        )

        sum_reward_mutual = self._reward_mutual_pair * gp.quicksum(
            1 - var for var in variables.mutual_unrealized.values()
        )

        sum_penalties_unassigned = self._penalty_unassigned * gp.quicksum(
            variables.unassigned_students.values()
        )

        establish_groups = variables.establish_groups
        sum_penalties_surplus_groups = gp.quicksum(
            penalty_surplus_group * establish_groups[project_id, group_id]
            for project_id, penalty_surplus_group, num_groups_desired in zip(
                self._project_ids,
                self._projects_info["pen_groups"],
                self._projects_info["desired#groups"],
            )
            for group_id in self._group_ids[project_id][num_groups_desired:]
        )

        group_size_surplus = variables.group_size_surplus
        group_size_deficit = variables.group_size_deficit

        sum_penalties_group_size = gp.quicksum(
            penalty_size_deviation
            * (group_size_surplus[project_id, group_id] + group_size_deficit[project_id, group_id])
            for project_id, penalty_size_deviation in enumerate(self._projects_info["pen_size"])
            for group_id in self._group_ids[project_id]
        )
        return LinExpressions(
            sum_realized_project_preferences=sum_realized_project_preferences,
            sum_reward_mutual=sum_reward_mutual,
            sum_penalties_unassigned=sum_penalties_unassigned,
            sum_penalties_surplus_groups=sum_penalties_surplus_groups,
            sum_penalties_group_size=sum_penalties_group_size,
        )

    def _set_objective(self, lin_expressions: LinExpressions):
        self._model.setObjective(
            lin_expressions.sum_realized_project_preferences
            + lin_expressions.sum_reward_mutual
            - lin_expressions.sum_penalties_unassigned
            - lin_expressions.sum_penalties_surplus_groups
            - lin_expressions.sum_penalties_group_size,
            sense=GRB.MAXIMIZE,
        )

    def _add_constraints(self, variables: Variables) -> InitialConstraints:
        assign_students = variables.assign_students
        unassigned_students = variables.unassigned_students
        establish_groups = variables.establish_groups
        group_size_surplus = variables.group_size_surplus
        group_size_deficit = variables.group_size_deficit
        mutual_unrealized = variables.mutual_unrealized

        one_assignment_or_unassigned = self._model.addConstrs(
            (
                assign_students.sum("*", "*", student_id) + unassigned_students[student_id] == 1
                for student_id in self._student_ids
            ),
            name="one_assignment_or_unassigned",
        )

        open_groups_consecutively = self._model.addConstrs(
            (
                establish_groups[project_id, group_id]
                <= establish_groups[project_id, group_id - 1]
                for project_id, group_id in self._project_group_pairs
                if group_id > 0
            ),
            name="open_groups_consecutively",
        )

        min_group_size_if_open = self._model.addConstrs(
            (
                assign_students.sum(project_id, group_id, "*")
                >= min_group_size * establish_groups[project_id, group_id]
                for project_id, min_group_size in enumerate(self._projects_info["min_group_size"])
                for group_id in self._group_ids[project_id]
            ),
            name="min_group_size_if_open",
        )

        max_group_size_if_open = self._model.addConstrs(
            (
                assign_students.sum(project_id, group_id, "*")
                <= max_group_size * establish_groups[project_id, group_id]
                for project_id, max_group_size in enumerate(self._projects_info["max_group_size"])
                for group_id in self._group_ids[project_id]
            ),
            name="max_group_size_if_open",
        )

        lower_bound_group_size_surplus = self._model.addConstrs(
            (
                group_size_surplus[project_id, group_id]
                >= assign_students.sum(project_id, group_id, "*") - ideal_group_size
                for project_id, ideal_group_size in enumerate(
                    self._projects_info["ideal_group_size"]
                )
                for group_id in self._group_ids[project_id]
            ),
            name="lower_bound_group_size_surplus",
        )

        lower_bound_group_size_deficit = self._model.addConstrs(
            (
                group_size_deficit[project_id, group_id]
                >= ideal_group_size
                - assign_students.sum(project_id, group_id, "*")
                - max_group_size * (1 - establish_groups[project_id, group_id])
                for (project_id, ideal_group_size), max_group_size in zip(
                    enumerate(self._projects_info["ideal_group_size"]),
                    self._projects_info["max_group_size"],
                )
                for group_id in self._group_ids[project_id]
            ),
            name="lower_bound_group_size_deficit",
        )

        max_num_groups = max(self._projects_info["max#groups"])

        unique_group_identifiers = {
            (project_id, group_id): project_id + group_id / max_num_groups
            for project_id, group_id in self._project_group_pairs
        }

        num_projects = len(self._projects_info)

        only_reward_materialized_pairs_1 = self._model.addConstrs(
            (
                (mutual_unrealized[first, second] - unassigned_students[first]) * num_projects
                >= sum(
                    unique_group_identifiers[project_id, group_id]
                    * (
                        assign_students[project_id, group_id, first]
                        - assign_students[project_id, group_id, second]
                    )
                    for project_id, group_id in self._project_group_pairs
                )
                for first, second in self._mutual_pairs
            ),
            name="only_reward_materialized_pairs_1",
        )

        only_reward_materialized_pairs_2 = self._model.addConstrs(
            (
                (mutual_unrealized[first, second] - unassigned_students[second]) * num_projects
                >= sum(
                    unique_group_identifiers[project_id, group_id]
                    * (
                        assign_students[project_id, group_id, second]
                        - assign_students[project_id, group_id, first]
                    )
                    for project_id, group_id in self._project_group_pairs
                )
                for first, second in self._mutual_pairs
            ),
            name="only_reward_materialized_pairs_2",
        )

        return InitialConstraints(
            one_assignment_or_unassigned=cast(
                gp.tupledict[int, gp.Constr], one_assignment_or_unassigned
            ),
            open_groups_consecutively=cast(
                gp.tupledict[int, gp.Constr], open_groups_consecutively
            ),
            min_group_size_if_open=cast(
                gp.tupledict[tuple[int, int, int], gp.Constr], min_group_size_if_open
            ),
            max_group_size_if_open=cast(
                gp.tupledict[tuple[int, int, int], gp.Constr], max_group_size_if_open
            ),
            lower_bound_group_size_surplus=cast(
                gp.tupledict[tuple[int, int, int], gp.Constr], lower_bound_group_size_surplus
            ),
            lower_bound_group_size_deficit=cast(
                gp.tupledict[tuple[int, int, int, int], gp.Constr], lower_bound_group_size_deficit
            ),
            only_reward_materialized_pairs_1=cast(
                gp.tupledict[tuple[int, int], gp.Constr], only_reward_materialized_pairs_1
            ),
            only_reward_materialized_pairs_2=cast(
                gp.tupledict[tuple[int, int], gp.Constr], only_reward_materialized_pairs_2
            ),
        )

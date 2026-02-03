"""Dataclasses that provide references to the components of an instance of the SSPAGDP."""

import dataclasses

import gurobipy


@dataclasses.dataclass(frozen=True)
class Variables:
    """Access to variables by their indexes."""

    assign_students: gurobipy.tupledict[tuple[int, int, int], gurobipy.Var]
    establish_groups: gurobipy.tupledict[tuple[int, int], gurobipy.Var]
    mutual_unrealized: gurobipy.tupledict[tuple[int, int], gurobipy.Var]
    unassigned_students: gurobipy.tupledict[int, gurobipy.Var]
    group_size_surplus: gurobipy.tupledict[tuple[int, int], gurobipy.Var]
    group_size_deficit: gurobipy.tupledict[tuple[int, int], gurobipy.Var]


@dataclasses.dataclass(frozen=True)
class LinExpressions:
    """Access to linear expressions."""

    sum_realized_project_preferences: gurobipy.LinExpr
    sum_reward_mutual: gurobipy.LinExpr
    sum_penalties_unassigned: gurobipy.LinExpr
    sum_penalties_surplus_groups: gurobipy.LinExpr
    sum_penalties_group_size: gurobipy.LinExpr


@dataclasses.dataclass(frozen=True)
class InitialConstraints:
    """Access to constraints of the base model by their indexes."""

    one_assignment_or_unassigned: gurobipy.tupledict[int, gurobipy.Constr]
    open_groups_consecutively: gurobipy.tupledict[int, gurobipy.Constr]
    min_group_size_if_open: gurobipy.tupledict[tuple[int, int, int], gurobipy.Constr]
    max_group_size_if_open: gurobipy.tupledict[tuple[int, int, int], gurobipy.Constr]
    lower_bound_group_size_surplus: gurobipy.tupledict[tuple[int, int, int], gurobipy.Constr]
    lower_bound_group_size_deficit: gurobipy.tupledict[tuple[int, int, int, int], gurobipy.Constr]
    only_reward_materialized_pairs_1: gurobipy.tupledict[tuple[int, int], gurobipy.Constr]
    only_reward_materialized_pairs_2: gurobipy.tupledict[tuple[int, int], gurobipy.Constr]


@dataclasses.dataclass(frozen=True)
class ModelComponents:
    """Access to the components of an instance of the SSPAGDP"""

    variables: Variables
    lin_expressions: LinExpressions
    initial_constraints: InitialConstraints

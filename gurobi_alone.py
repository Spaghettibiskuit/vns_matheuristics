"""Solving instances of the SSPAGDP with Gurobi alone outside further algorithms.

SSPAGDP := Simultaneous Student-Project Allocation and Group Design Problem
"""

import random

from model_wrappers.thin_wrappers import GurobiAloneWrapper
from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from solution_processing.post_processing import post_processing
from solution_processing.solution_access import SolutionAccess


def gurobi_alone(
    number_of_projects: int,
    number_of_students: int,
    instance_index: int,
    reward_mutual_pair: int = 2,
    penalty_unassigned: int = 3,
    time_limit: int | float = 60,
) -> SolutionAccess:
    """Return class that allows to view, save and assess solution after running Gurobi.

    Args:
        number_of_project: The number of projects.
        number_of_students: The number of students.
        instance_index: The index of the instance among those with the same number of projects as
            well as the same number of students.

        reward_mutual_pair: The reward for when two students that want to work with each other are
            in the same group.
        penalty_unassigned: The penalty per student who is not assigned to any group.

        time_limit: The time the algorithm is allowed to run.
    """
    config = Configuration.get(
        number_of_projects=number_of_projects,
        number_of_students=number_of_students,
        instance_index=instance_index,
        reward_mutual_pair=reward_mutual_pair,
        penalty_unassigned=penalty_unassigned,
    )
    derived = DerivedModelingData.get(config=config)
    model = GurobiAloneWrapper(config, derived)
    model.set_time_limit(time_limit)
    model.optimize()
    return post_processing(model.start_time, config, derived, model)


if __name__ == "__main__":
    random.seed(0)
    gurobi_alone(30, 300, 0)

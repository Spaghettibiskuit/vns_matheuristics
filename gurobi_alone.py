import random
import time

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
    config = Configuration.get(
        number_of_projects=number_of_projects,
        number_of_students=number_of_students,
        instance_index=instance_index,
        reward_mutual_pair=reward_mutual_pair,
        penalty_unassigned=penalty_unassigned,
    )
    derived = DerivedModelingData.get(config=config)
    start_time = time.time()
    model = GurobiAloneWrapper(config, derived)
    model.set_time_limit(time_limit)
    model.optimize()
    return post_processing(start_time, config, derived, model)


if __name__ == "__main__":
    random.seed(0)
    gurobi_alone(30, 300, 0)

import random
import time

import gurobipy

from model_wrappers.local_brancher import LocalBrancher
from model_wrappers.thin_wrappers import Initializer
from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from solution_processing.post_processing import post_processing
from solution_processing.solution_access import SolutionAccess


def local_branching(
    number_of_projects: int,
    number_of_students: int,
    instance_index: int,
    reward_mutual_pair: int = 2,
    penalty_unassigned: int = 3,
    total_time_limit: int | float = 60,
    shake_min_perc: int | float = 10,
    shake_step_perc: int | float = 10,
    shake_max_perc: int | float = 40,
    rhs_min_perc: int | float = 10,
    rhs_step_perc: int | float = 10,
    rhs_max_perc: int | float = 40,
    initial_patience: float | int = 6,
    shake_patience: float | int = 6,
    step_shake_patience: float | int = 0.6,
    base_optimization_patience: int | float = 6,
    step_optimization_patience: int | float = 0.6,
    required_initial_solutions: int = 5,
    drop_branching_constrs_before_shake: bool = False,
) -> SolutionAccess:
    config = Configuration.get(
        number_of_projects=number_of_projects,
        number_of_students=number_of_students,
        instance_index=instance_index,
        reward_mutual_pair=reward_mutual_pair,
        penalty_unassigned=penalty_unassigned,
    )
    derived = DerivedModelingData.get(config=config)
    max_num_assignment_changes = config.number_of_students * 2
    shake_min, shake_step, shake_max, rhs_min, rhs_step, rhs_max = (
        round(percentage / 100 * max_num_assignment_changes)
        for percentage in (
            shake_min_perc,
            shake_step_perc,
            shake_max_perc,
            rhs_min_perc,
            rhs_step_perc,
            rhs_max_perc,
        )
    )

    initial_model = Initializer(
        config=config, derived=derived, required_sol_count=required_initial_solutions
    )
    start_time = initial_model.start_time

    shake_cur = shake_min - shake_step

    initial_model.set_time_limit(total_time_limit, start_time)
    initial_model.optimize(patience=initial_patience)

    model = LocalBrancher.get(initial_model)

    while not time.time() - start_time > total_time_limit:
        rhs = rhs_min
        patience = base_optimization_patience

        while not time.time() - start_time > total_time_limit:
            if rhs > rhs_max:
                break

            patience = base_optimization_patience / rhs_min * rhs

            model.set_time_limit(total_time_limit, start_time)

            model.add_bounding_branching_constraint(rhs)
            print(f"\n\nPATIENCE: {patience}\n\n")
            model.optimize(patience)
            model.pop_branching_constraints_stack()

            if model.solution_count == 0:
                break

            if model.improvement_infeasible():
                if rhs > rhs_min:
                    model.pop_branching_constraints_stack()
                model.add_excluding_branching_constraint(rhs)
                rhs += rhs_step

            elif model.improvement_found():
                model.store_solution()
                if model.status == gurobipy.GRB.OPTIMAL:
                    if rhs > rhs_min:
                        model.pop_branching_constraints_stack()
                    model.add_excluding_branching_constraint(rhs)
                rhs = rhs_min

            else:
                break

        base_optimization_patience += step_optimization_patience

        if model.new_best_found():
            model.make_current_solution_best_solution()
            shake_cur = shake_min
        else:
            shake_cur += shake_step
            if shake_cur > shake_max:
                shake_cur = shake_min
        if drop_branching_constrs_before_shake:
            model.drop_all_branching_constraints()

        model.make_best_solution_current_solution()

        model.add_shaking_constraints(shake_cur, shake_step)
        model.set_time_limit(total_time_limit, start_time)
        print(
            f"\n\n PATIENCE: {shake_patience}; SHAKE: {shake_cur}-{shake_cur + shake_step} "
            f" ({config.number_of_students})\n\n"
        )
        model.optimize(shake_patience, shake=True)
        shake_patience += step_shake_patience
        model.remove_shaking_constraints()

        if model.solution_count == 0:
            break

        model.store_solution()
        if model.new_best_found():
            model.make_current_solution_best_solution()
            shake_cur = shake_min - shake_step

        model.increment_random_seed()

    model.drop_all_branching_constraints()
    model.recover_to_best_found()
    return post_processing(start_time, config, derived, model)


if __name__ == "__main__":
    random.seed(0)
    local_branching(30, 300, 0, total_time_limit=10_000)

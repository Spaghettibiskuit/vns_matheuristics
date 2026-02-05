"""The assignment-based local branching algorithm for the SSPAGDP.

SSPAGDP := Simultaneous Student-Project Allocation and Group Design Problem
"""

import random
import time

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
    time_limit: int | float = 60,
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
) -> SolutionAccess:
    """Return class that allows to view, save and assess solution after running heuristic.

    Args:
        number_of_project: The number of projects.
        number_of_students: The number of students.
        instance_index: The index of the instance among those with the same dimension, i.e the same
            number of projects as well as the same number of students.
        reward_mutual_pair: The reward for when two students that want to work with each other are
            in the same group.
        penalty_unassigned: The penalty per student who is not assigned to any group.
        time_limit: The time the algorithm is allowed to run.
        shake_min_perc: In each shake, for a solution to be valid, for the percentage p of
            assignments that are different from the best solution
            shake_current_perc <= p <= shake_current_perc + shake_step_perc. shake_min_perc is the
            minimum for shake_current_perc.
        shake_step_perc: The size of the subproblems during the shake, since for a solution to be
            valid, for the percentage p of assignments that are different from the best solution
            shake_current_perc <= p <= shake_current_perc + shake_step_perc. If no new best
            solution is found in the VND after a shake and shake_current_perc is not yet at its
            maximum value, for the next shake,
            shake_current_perc = min(shake_current_perc + shake_step_perc, shake_max_perc).
        shake_max_perc: In each shake, for a solution to be valid, for the percentage p of
            assignments that are different from the best solution
            shake_current_perc <= p <= shake_current_perc + shake_step_perc. shake_max_perc is the
            maximum for shake_current_perc. If shake_current_perc == shake_max_perc,
            shake_cur_percentage == shake_min_perc for the next shake.
        rhs_min_perc: During VND for, a solution to be valid, the percentage p of assignments that
            are different from the current solution p <= rhs_perc. rhs_min_perc is the minimum for
            rhs_perc.
        rhs_step_perc: During VND, for a solution to be valid, the percentage p of assignments that
            are different from the current solution p <= rhs_perc. If it was proven that for any
            p <= rhs_perc an improvement is infeasible, the rhs_perc += rhs_step_perc for the next
            search during VND.
        rhs_max_perc: During VND, for a solution to be valid, the percentage p of assignments that
            are different from the current solution p <= rhs_perc. rhs_max_perc is the maximum for
            rhs_perc.
        initial_patience: The patience in seconds during the initial optimization.
        shake_patience: The patience in seconds during the shake before any increases.
        shake_patience_step: The increase in seconds of the patience during the shake for every new
            shake i.e. after each shake, shake_patience += shake_patience_step.
        base_optimization_patience: The patience inside VND at the beginning if
            rhs_perc == rhs_min_perc. The patience grows proportional with rhs_perc.
        step_optimization_patience: The increase in patience for every new VND after the first for
            rhs_perc == rhs_min_perc. The patience grows proportional with rhs_perc, hence for
            rhs_perc == 2 * rhs_min_perc, the increase is double.
        required_initial_solutions: The number of solutions Gurobi has to find before initial
            optimization can stop.
    """
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

    initial_model = Initializer(config, derived, required_initial_solutions)
    start_time = initial_model.start_time

    shake_cur = shake_min - shake_step

    initial_model.set_time_limit(time_limit)
    initial_model.optimize(patience=initial_patience)

    model = LocalBrancher.get(initial_model)

    while time.time() - start_time < time_limit:
        rhs = rhs_min

        while time.time() - start_time < time_limit:
            patience = base_optimization_patience / rhs_min * rhs

            model.set_time_limit(time_limit)

            model.add_bounding_branching_constraint(rhs)
            print(f"\n\nPATIENCE: {patience}\n\n")
            model.optimize(patience)
            model.pop_branching_constraints_stack()

            if model.solution_count == 0:
                break

            if model.improvement_infeasible():
                if rhs > rhs_min:
                    # This means an excluding branching constrains with the same solution as
                    # reference and a smaller right-hand side is now on top of the constraints
                    # stack. This one will be redundant once we add one with with a larger
                    # right-hand side.
                    model.pop_branching_constraints_stack()
                model.add_excluding_branching_constraint(rhs)
                if rhs == rhs_max:
                    break
                rhs = min(rhs + rhs_step, rhs_max)

            elif model.improvement_found():
                if model.solution_is_optimal():
                    if rhs > rhs_min:
                        model.pop_branching_constraints_stack()
                    model.add_excluding_branching_constraint(rhs)
                model.store_solution()
                rhs = rhs_min

            else:
                break

        base_optimization_patience += step_optimization_patience

        if model.new_best_found():
            model.make_current_solution_best_solution()
            shake_cur = shake_min
        elif shake_cur == shake_max:
            shake_cur = shake_min
        else:
            shake_cur = min(shake_cur + shake_step, shake_max)

        model.drop_all_branching_constraints()
        model.make_best_solution_current_solution()

        model.add_shaking_constraints(shake_cur, shake_step)
        model.set_time_limit(time_limit)
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
    local_branching(30, 300, 0, time_limit=10_000)

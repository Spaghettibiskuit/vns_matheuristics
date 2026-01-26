import itertools
import random
import time

from model_wrappers.assignment_fixer import AssignmentFixer
from model_wrappers.thin_wrappers import Initializer
from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from solution_processing.post_processing import post_processing
from solution_processing.solution_access import SolutionAccess
from solving_utilities.patience_manager import PatienceManager


def assignment_fixing(
    number_of_projects: int,
    number_of_students: int,
    instance_index: int,
    reward_mutual_pair: int = 2,
    penalty_unassigned: int = 3,
    time_limit: int | float = 60,
    min_num_zones: int = 4,
    max_num_zones: int = 6,
    min_shake_perc: int = 10,
    step_shake_perc: int = 10,
    max_shake_perc: int = 40,
    initial_patience: int | float = 3,
    shake_patience: int | float = 3,
    shake_patience_step: int | float = 0.9,
    base_optimization_patience: int | float = 3,
    base_optimization_patience_step: float = 0.3,
    required_initial_solutions: int = 5,
) -> SolutionAccess:
    config = Configuration.get(
        number_of_projects=number_of_projects,
        number_of_students=number_of_students,
        instance_index=instance_index,
        reward_mutual_pair=reward_mutual_pair,
        penalty_unassigned=penalty_unassigned,
    )
    derived = DerivedModelingData.get(config)
    min_shake, step_shake, max_shake = (
        round(percentage / 100 * config.number_of_students)
        for percentage in (min_shake_perc, step_shake_perc, max_shake_perc)
    )

    shake_cur = min_shake - step_shake

    initial_model = Initializer(config, derived, required_initial_solutions)
    start_time = initial_model.start_time

    initial_model.set_time_limit(time_limit)
    initial_model.optimize(initial_patience)

    model = AssignmentFixer.get(initial_model)
    patience_manager = PatienceManager(
        min_num_zones,
        max_num_zones,
        base_optimization_patience,
        base_optimization_patience_step,
    )

    while time.time() - start_time < time_limit:
        current_num_zones = max_num_zones

        free_zones_pairs = itertools.combinations(range(current_num_zones), 2)
        new_pairs = False

        while time.time() - start_time < time_limit:
            if new_pairs:
                free_zones_pairs = itertools.combinations(range(current_num_zones), 2)
                new_pairs = False

            if (free_zones_pair := next(free_zones_pairs, None)) is None:
                patience_manager.adjust_patience(current_num_zones)
                if current_num_zones == min_num_zones:
                    break
                new_pairs = True
                current_num_zones -= 1
                continue

            model.fix_rest(*free_zones_pair, current_num_zones)
            model.set_time_limit(time_limit)
            patience = patience_manager.patiences[current_num_zones]
            print(
                f"\nCURRENT NUM ZONES:{current_num_zones}, PAIR: {free_zones_pair}, PATIENCE: {patience}\n"
            )
            model.optimize(patience)

            if model.solution_count == 0:
                break

            if model.improvement_found():
                model.store_solution()
                new_pairs = True
                current_num_zones = max_num_zones

        if model.new_best_found():
            model.make_current_solution_best_solution()
            shake_cur = min_shake
        elif shake_cur == max_shake:
            shake_cur = min_shake
        else:
            shake_cur = min(shake_cur + step_shake, max_shake)

        model.make_best_solution_current_solution()

        model.force_k_worst_to_change(shake_cur)
        model.set_time_limit(time_limit)

        print(f"\n\nPATIENCE: {shake_patience}; FORCED TO MOVE: {shake_cur}\n\n")

        model.optimize(shake_patience, shake=True)

        shake_patience += shake_patience_step
        model.free_all_unassigned_vars()

        if model.solution_count == 0:
            break

        model.store_solution()
        if model.new_best_found():
            model.make_current_solution_best_solution()
            shake_cur = min_shake - step_shake

        model.increment_random_seed()
        model.delete_zoning_rules()

    model.recover_to_best_found()
    return post_processing(start_time, config, derived, model)


if __name__ == "__main__":
    random.seed(0)
    assignment_fixing(30, 300, 0, time_limit=600)

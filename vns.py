import itertools
import random
import time

import gurobipy

from model_wrappers.assignment_fixer import AssignmentFixer
from model_wrappers.local_brancher import LocalBrancher
from model_wrappers.thin_wrappers import GurobiAloneWrapper, Initializer
from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from solution_processing.solution_access import SolutionAccess
from solution_processing.solution_checker import SolutionChecker
from solution_processing.solution_info_retriever import SolutionInformationRetriever
from solution_processing.solution_viewer import SolutionViewer
from solving_utilities.patience_manager import PatienceManager


class VariableNeighborhoodSearch:

    def __init__(
        self,
        number_of_projects: int,
        number_of_students: int,
        instance_index: int,
        reward_mutual_pair: int = 2,
        penalty_unassigned: int = 3,
    ):
        self.config = Configuration.get(
            number_of_projects=number_of_projects,
            number_of_students=number_of_students,
            instance_index=instance_index,
            reward_mutual_pair=reward_mutual_pair,
            penalty_unassigned=penalty_unassigned,
        )
        self.derived = DerivedModelingData.get(config=self.config)
        self.best_model = None
        self.best_solution = None

    def gurobi_alone(self, time_limit: int | float = float("inf")) -> list[dict[str, int | float]]:
        start_time = time.time()
        model = GurobiAloneWrapper(
            config=self.config,
            derived=self.derived,
        )
        model.set_time_limit(time_limit)
        model.optimize()

        self.best_model = model
        self._post_processing(start_time)
        return model.solution_summaries

    def local_branching(
        self,
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
    ):
        max_num_assignment_changes = self.config.number_of_students * 2
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
            config=self.config, derived=self.derived, required_sol_count=required_initial_solutions
        )
        start_time = initial_model.start_time

        shake_cur = shake_min - shake_step

        initial_model.set_time_limit(total_time_limit, start_time)
        initial_model.optimize(patience=initial_patience)

        model = LocalBrancher.get(initial_model)

        while not self._time_over(start_time, total_time_limit):
            rhs = rhs_min
            patience = base_optimization_patience

            while not self._time_over(start_time, total_time_limit):
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
                f" ({self.config.number_of_students})\n\n"
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
        self.best_model = model
        self._post_processing(start_time)
        return model.solution_summaries

    def assignment_fixing(
        self,
        total_time_limit: int | float = 60,
        min_num_zones: int = 4,
        max_num_zones: int = 6,
        min_shake_perc: int = 10,
        step_shake_perc: int = 10,
        max_shake_perc: int = 40,
        initial_patience: int | float = 3,
        shake_patience: int | float = 3,
        shake_patience_step: int | float = 0.3,
        base_optimization_patience: int | float = 3,
        base_optimization_patience_step: float = 0.3,
        required_initial_solutions: int = 5,
    ):
        min_shake, step_shake, max_shake = (
            round(percentage / 100 * self.config.number_of_students)
            for percentage in (min_shake_perc, step_shake_perc, max_shake_perc)
        )

        shake_cur = min_shake - step_shake

        initial_model = Initializer(self.config, self.derived, required_initial_solutions)
        start_time = initial_model.start_time

        initial_model.set_time_limit(total_time_limit, start_time)
        initial_model.optimize(initial_patience)

        model = AssignmentFixer.get(initial_model)
        patience_manager = PatienceManager(
            min_num_zones,
            max_num_zones,
            base_optimization_patience,
            base_optimization_patience_step,
        )

        while not self._time_over(start_time, total_time_limit):
            current_num_zones = max_num_zones

            free_zones_pairs = itertools.combinations(range(current_num_zones), 2)
            new_pairs = False

            while not self._time_over(start_time, total_time_limit):
                if new_pairs:
                    free_zones_pairs = itertools.combinations(range(current_num_zones), 2)
                    new_pairs = False

                if (free_zones_pair := next(free_zones_pairs, None)) is None:
                    patience_manager.adjust_patience(current_num_zones)
                    if current_num_zones == min_num_zones:
                        break
                    new_pairs = True
                    current_num_zones = max(current_num_zones - 1, min_num_zones)
                    continue

                model.fix_rest(*free_zones_pair, current_num_zones)
                model.set_time_limit(total_time_limit, start_time)
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

            model.delete_zoning_rules()

            model.make_best_solution_current_solution()

            model.force_k_worst_to_change(shake_cur)
            model.set_time_limit(total_time_limit, start_time)

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

        model.recover_to_best_found()
        self.best_model = model
        self._post_processing(start_time)
        return model.solution_summaries

    def _time_over(self, start_time: float, total_time_limit: int | float):
        return time.time() - start_time > total_time_limit

    def _post_processing(self, start_time: float):
        if self.best_model is None:
            raise TypeError("No postprocessing possible if best model is None.")
        retriever = SolutionInformationRetriever(
            config=self.config,
            derived=self.derived,
            variables=self.best_model.model_components.variables,
        )
        viewer = SolutionViewer(retriever)
        checker = SolutionChecker(
            lin_expressions=self.best_model.model_components.lin_expressions,
            retriever=retriever,
        )
        self.best_solution = SolutionAccess(
            model=self.best_model,
            retriever=retriever,
            viewer=viewer,
            checker=checker,
        )
        if checker.is_correct:
            print("IS CORRECT")
        else:
            print("IS INCORRECT")
        self.best_model.solution_summaries.append(
            {"is_correct": int(checker.is_correct), "runtime": time.time() - start_time}
        )


if __name__ == "__main__":
    random.seed(0)
    vns = VariableNeighborhoodSearch(30, 300, 0)
    vns.assignment_fixing(total_time_limit=60)

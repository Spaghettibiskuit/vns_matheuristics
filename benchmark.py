import dataclasses
import enum
import json
import random
from pathlib import Path

import utilities
from assignment_fixing import assignment_fixing
from gurobi_alone import gurobi_alone
from local_branching import local_branching
from model_wrappers.assignment_fixer import AssignmentFixer
from model_wrappers.local_brancher import LocalBrancher
from model_wrappers.thin_wrappers import GurobiAloneWrapper


class Subfolders(enum.StrEnum):
    GUROBI = "gurobi"
    LOCAL_BRANCHING = "local_branching"
    VARIABLE_FIXING = "variable_fixing"


@dataclasses.dataclass
class LocalBranchingParameters:
    time_limit: int | float = 60
    initial_patience: float | int = 0
    shake_patience: float | int = 0
    step_shake_patience: float | int = 0
    base_optimization_patience: int | float = 0
    step_optimization_patience: int | float = 0


@dataclasses.dataclass
class AssignmentFixingParamters:
    time_limit: int | float = 60
    min_num_zones: int = 4
    max_num_zones: int = 6
    initial_patience: int | float = 0
    shake_patience: int | float = 0
    shake_patience_step: int | float = 0
    base_optimization_patience: int | float = 0
    base_optimization_patience_step: float = 0


@dataclasses.dataclass
class GurobiAloneParameters:
    time_limit: int | float = 60


def check_whether_instances_exist(instances: list[tuple[int, int, int]]):
    for instance in instances:
        path_projects, path_students = utilities.build_paths(*instance)
        if not path_projects.exists():
            raise ValueError(f"{path_projects} does not exist")
        if not path_students.exists():
            raise ValueError(f"{path_students} does not exist")


def get_path(method: str, name: str):
    return Path("benchmarks") / method / (name + ".json")


def benchmark_instance_gurobi_alone(
    instance: tuple[int, int, int], parameters: GurobiAloneParameters
) -> list[dict[str, int | float]]:
    solution_access = gurobi_alone(*instance, **dataclasses.asdict(parameters))
    if not isinstance(solution_access.model, GurobiAloneWrapper):
        raise TypeError()
    return solution_access.model.solution_summaries


def benchmark_instance_local_branching(
    instance: tuple[int, int, int], parameters: LocalBranchingParameters
) -> list[dict[str, int | float | str]]:
    solution_access = local_branching(*instance, **dataclasses.asdict(parameters))
    if not isinstance(solution_access.model, LocalBrancher):
        raise TypeError()
    return solution_access.model.solution_summaries


def benchmark_instance_variable_fixing(
    instance: tuple[int, int, int], parameters: AssignmentFixingParamters
) -> list[dict[str, int | float | str]]:
    solution_access = assignment_fixing(*instance, **dataclasses.asdict(parameters))
    if not isinstance(solution_access.model, AssignmentFixer):
        raise TypeError()
    return solution_access.model.solution_summaries


def benchmark(
    name: str,
    run_gurobi_alone: bool,
    run_local_branching: bool,
    run_variable_fixing: bool,
    instances: list[tuple[int, int, int]],
    gurobi_alone_parameters: GurobiAloneParameters = GurobiAloneParameters(),
    local_branching_parameters: LocalBranchingParameters = LocalBranchingParameters(),
    variable_fixing_parameters: AssignmentFixingParamters = AssignmentFixingParamters(),
    seed: int = 0,
):
    check_whether_instances_exist(instances)

    gurobi_path = get_path(Subfolders.GUROBI, name)
    local_branching_path = get_path(Subfolders.LOCAL_BRANCHING, name)
    variable_fixing_path = get_path(Subfolders.VARIABLE_FIXING, name)

    for path, will_be_written_to in (
        (gurobi_path, run_gurobi_alone),
        (local_branching_path, run_local_branching),
        (variable_fixing_path, run_variable_fixing),
    ):
        if path.exists() and will_be_written_to:
            raise ValueError(f"{path} that will be written to already exists.")

    gurobi_solutions: dict[str, list[dict[str, int | float]]] = {}
    local_branching_solutions: dict[str, list[dict[str, int | float | str]]] = {}
    variable_fixing_solutions: dict[str, list[dict[str, int | float | str]]] = {}

    for instance in instances:

        key = "_".join(str(elem) for elem in instance)

        if run_gurobi_alone:
            random.seed(seed)
            gurobi_solutions[key] = benchmark_instance_gurobi_alone(
                instance, gurobi_alone_parameters
            )
            gurobi_path.write_text(json.dumps(gurobi_solutions, indent=4), encoding="utf-8")

        num_projects = instance[0]

        if run_local_branching:
            random.seed(seed)
            patience = num_projects / 10 * 3
            local_branching_parameters.initial_patience = patience
            local_branching_parameters.shake_patience = patience
            local_branching_parameters.base_optimization_patience = patience

            local_branching_parameters.step_shake_patience = patience / 10
            local_branching_parameters.step_optimization_patience = patience / 10

            local_branching_solutions[key] = benchmark_instance_local_branching(
                instance, local_branching_parameters
            )
            local_branching_path.write_text(
                json.dumps(local_branching_solutions, indent=4), encoding="utf-8"
            )

        if run_variable_fixing:
            random.seed(seed)
            patience = num_projects / 10
            variable_fixing_parameters.initial_patience = patience
            variable_fixing_parameters.shake_patience = patience
            variable_fixing_parameters.base_optimization_patience = patience
            variable_fixing_parameters.base_optimization_patience_step = patience / 10
            variable_fixing_parameters.shake_patience_step = (
                (
                    variable_fixing_parameters.max_num_zones
                    - variable_fixing_parameters.min_num_zones
                    + 1
                )
                * patience
                / 10
            )

            variable_fixing_solutions[key] = benchmark_instance_variable_fixing(
                instance, variable_fixing_parameters
            )
            variable_fixing_path.write_text(
                json.dumps(variable_fixing_solutions, indent=4), encoding="utf-8"
            )


if __name__ == "__main__":
    benchmark(
        name="test",
        run_gurobi_alone=True,
        run_local_branching=True,
        run_variable_fixing=True,
        instances=[(i * 10, i * 100, j) for i in [3, 7, 10] for j in range(0, 1)],
        gurobi_alone_parameters=GurobiAloneParameters(time_limit=60),
        local_branching_parameters=LocalBranchingParameters(time_limit=180),
        variable_fixing_parameters=AssignmentFixingParamters(time_limit=180),
    )

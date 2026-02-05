"""Functions and Enums that are useful throughout the project."""

import collections.abc
import enum
import json
import pathlib

import gurobipy
import pandas


class Subfolders(enum.StrEnum):
    """The subfolders of the benchmark folder in which benchmarks of each method belong."""

    GUROBI = "gurobi"
    LOCAL_BRANCHING = "local_branching"
    VARIABLE_FIXING = "variable_fixing"


class Stations(enum.StrEnum):
    """The different stations during the optimization with local branching or assignment fixing."""

    INITIAL_OPTIMIZATION = "initial_optimization"
    VND = "vnd"
    SHAKE = "shake"


def var_values(variables: collections.abc.Iterable[gurobipy.Var]) -> tuple[float, ...]:
    """Return just the variables values sorted by their index position."""
    return tuple(var.X for var in variables)


def gurobi_round(value: float) -> int:
    """Return the rounded value while checking for deviations beyond numeric reasons.

    The objective value and other values can only be integer valued for our instances. The float
    values of Gurobi have a tolerance of 1e-4. If the deviation to the closest integer is greater,
    an exception is raised.
    """
    if abs(value - (rounded := round(value))) > 1e-4:  # 1e-4 is Gurobi's tolerance
        raise ValueError("Unexpectedly large deviation from closest integer.")
    return rounded


def build_paths(
    num_projects: int, num_students: int, instance_index: int
) -> tuple[pathlib.Path, pathlib.Path]:
    """Return the paths to info on the students and that on the projects that make an instance."""
    directory = pathlib.Path("instances") / f"{num_projects}_projects_{num_students}_students"
    prefix, suffix = f"{num_projects}_{num_students}_", f"_{instance_index}.csv"
    return directory / f"{prefix}projects{suffix}", directory / f"{prefix}students{suffix}"


def load_instance(
    num_projects: int, num_students: int, instance_index: int
) -> tuple[pandas.DataFrame, pandas.DataFrame]:
    """Return the specified instance of the SSPAGDP."""
    path_projects, path_students = build_paths(num_projects, num_students, instance_index)
    projects: pandas.DataFrame = pandas.read_csv(path_projects)  # type: ignore
    students: pandas.DataFrame = pandas.read_csv(path_students)  # type: ignore
    students["fav_partners"] = students["fav_partners"].apply(lambda x: frozenset(json.loads(x)))  # type: ignore
    students["project_prefs"] = students["project_prefs"].apply(lambda x: tuple(json.loads(x)))  # type: ignore
    return projects, students

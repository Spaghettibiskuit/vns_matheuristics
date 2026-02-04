"""Function that checks correctness and instantiates objects to assess solution.

Correct means that the solution is valid and that the objective value is calculated correctly.
To the solution summaries (a list of the best solutions at the time they were found) a final
dictionary is appended which states whether the solution was correct (1) or not (0).

The solution can be assessed via an instance of
solution_processing.solution_access.SolutionAccess which is a composite of objects which serve that
purpose.
"""

import time

from model_wrappers.model_wrapper import ModelWrapper
from model_wrappers.thin_wrappers import GurobiAloneWrapper
from modeling.configuration import Configuration
from modeling.derived_modeling_data import DerivedModelingData
from solution_processing.solution_access import SolutionAccess
from solution_processing.solution_checker import SolutionChecker
from solution_processing.solution_info_retriever import SolutionInformationRetriever
from solution_processing.solution_viewer import SolutionViewer


def post_processing(
    start_time: float,
    config: Configuration,
    derived: DerivedModelingData,
    model: ModelWrapper | GurobiAloneWrapper,
) -> SolutionAccess:
    """Check whether solution is correct and return a composite of objects to assess the solution.

    Correct means that the solution is valid and that the objective value is calculated correctly.
    To the solution summaries (a list of the best solutions at the time they were found) a final
    dictionary is appended which states whether the solution was correct (1) or not (0).
    """
    retriever = SolutionInformationRetriever(
        config=config,
        derived=derived,
        variables=model.model_components.variables,
    )
    viewer = SolutionViewer(retriever)
    checker = SolutionChecker(
        lin_expressions=model.model_components.lin_expressions,
        retriever=retriever,
    )
    if checker.is_correct:
        print("IS CORRECT")
    else:
        print("IS INCORRECT")
    model.solution_summaries.append(
        {"is_correct": int(checker.is_correct), "runtime": time.time() - start_time}
    )

    return SolutionAccess(
        model=model,
        retriever=retriever,
        viewer=viewer,
        checker=checker,
    )

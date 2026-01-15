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
):
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

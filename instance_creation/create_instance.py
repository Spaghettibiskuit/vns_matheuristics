"""Stores the parameters for randomly creating an instance as well as the function to do so.

An instance consists of two pandas.Dataframes. One for the projects and one for the students. The
random values are within the boundaries of or influenced by the parameters stored in ProjectsParams
and StudentsParams.

Typical usage example:
    - Set the parameters for the projects dataframe in ProjectsParams
    - Set the parameters for the students dataframe in StudentsParams
    - projects_df, students_df = create_instance(num_projects, num_students)
"""

import dataclasses

import pandas

from instance_creation.projects_info import random_projects_df
from instance_creation.students_info import random_students_df


@dataclasses.dataclass
class ProjectsParams:
    """The boundaries in between which random values are created for each project.

    Attributes and their values are used as key-value pairs by create_instance to call
    random_projects_df in instance_creation.projects_info. Refer to docstring of random_projects_df
    for further information on the meaning of the attributes.
    """

    min_desired_num_groups: int = 2
    max_desired_num_groups: int = 4
    min_manageable_surplus_groups: int = 1
    max_manageable_surplus_groups: int = 3
    min_ideal_group_size: int = 2
    max_ideal_group_size: int = 4
    min_tolerable_group_size_deficit: int = 1
    max_tolerable_group_size_deficit: int = 3
    min_tolerable_group_size_surplus: int = 1
    max_tolerable_group_size_surplus: int = 3
    min_pen_num_groups: int = 1
    max_pen_num_groups: int = 3
    min_pen_group_size: int = 1
    max_pen_group_size: int = 3


@dataclasses.dataclass
class StudentsParams:
    """Parameters that influence how random values are created for each student.

    Attributes and their values are used as key-value pairs by create_instance to call
    random_students_df in instance_creation.projects_info. Refer to docstring of random_students_df
    for further information on the meaning of the attributes.
    """

    min_num_partner_preferences: int = 1
    max_num_partner_preferences: int = 5
    percentage_reciprocity: float = 0.7
    percentage_peer_influenced_project_preferences: float = 0.7
    min_project_preference: int = 0
    max_project_preference: int = 3


def create_instance(
    num_projects: int, num_students: int
) -> tuple[pandas.DataFrame, pandas.DataFrame]:
    """Return random instance consisting of specifications for projects and students."""
    projects_info = random_projects_df(num_projects, **dataclasses.asdict(ProjectsParams()))
    students_info = random_students_df(
        num_projects, num_students, **dataclasses.asdict(StudentsParams())
    )
    return projects_info, students_info

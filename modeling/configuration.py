"""A class that contains all specifications that define an instance of the SSPAGDP."""

import dataclasses

import pandas

import utilities


@dataclasses.dataclass(frozen=True)
class Configuration:
    """Contains all all specifications that define an instance of the SSPAGDP.

    Attributes:
        number_of_projects: The number of projects.
        number_of_students: The number of students.
        instance_index: The index of the instance among those with the same number of projects and
            and number of students.
        penalty_unassigned: Penalty per student who is not assigned to any group.
        projects_info: Each project's constraints, whishes and penalties regarding the number of
            groups and group sizes. THE INDEX POSITION IN THE DATAFRAME IS THE PROJECT'S ID.
        students_info: For all students the project preference for every project and the preferred
            partners i.e., the students the student wants to work with. THE INDEX POSITION IN THE
            DATAFRAME is THE STUDENT'S ID.
    """

    number_of_projects: int
    number_of_students: int
    instance_index: int
    reward_mutual_pair: int
    penalty_unassigned: int

    projects_info: pandas.DataFrame
    students_info: pandas.DataFrame

    @classmethod
    def get(
        cls,
        number_of_projects: int,
        number_of_students: int,
        instance_index: int,
        reward_mutual_pair: int,
        penalty_unassigned: int,
    ) -> "Configuration":
        """Alternative Initializer for a frozen dataclass."""
        projects_info, students_info = utilities.load_instance(
            number_of_projects, number_of_students, instance_index
        )
        return cls(
            number_of_projects,
            number_of_students,
            instance_index,
            reward_mutual_pair,
            penalty_unassigned,
            projects_info,
            students_info,
        )

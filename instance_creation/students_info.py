"""Create random preferences regarding projects and group partners for a given number of students.

Every student expresses a preference for each available project. Every student also names other
students he/she would like to work with.
"""

import random

import pandas


def _random_partner_preferences(
    num_students: int,
    percentage_reciprocity: float,
    min_num_partner_prefs: int,
    max_num_partner_prefs: int,
) -> list[list[int]]:
    students_partner_prefs: list[list[int]] = []
    student_ids = list(range(num_students))
    chosen_by: dict[int, list[int]] = {student_id: [] for student_id in student_ids}

    for student_id in student_ids:
        all_other_ids = student_ids[:student_id] + student_ids[student_id + 1 :]
        num_partner_prefs = random.randint(min_num_partner_prefs, max_num_partner_prefs)

        if ids_that_chose_student := chosen_by[student_id]:
            applicable_for_reciprocity = random.sample(
                ids_that_chose_student,
                min(len(ids_that_chose_student), num_partner_prefs),
            )
            reciprocal_prefs = [
                applicable_id
                for applicable_id in applicable_for_reciprocity
                if random.random() <= percentage_reciprocity
            ]
            num_missing_prefs = num_partner_prefs - len(reciprocal_prefs)

            if not num_missing_prefs:
                student_partner_prefs = reciprocal_prefs
            else:
                left_options = [
                    student_id
                    for student_id in all_other_ids
                    if student_id not in reciprocal_prefs
                ]
                random_prefs = random.sample(left_options, num_missing_prefs)
                student_partner_prefs = reciprocal_prefs + random_prefs
        else:
            student_partner_prefs = random.sample(all_other_ids, num_partner_prefs)

        students_partner_prefs.append(student_partner_prefs)

        for partner_preference in student_partner_prefs:
            chosen_by[partner_preference].append(student_id)

    return students_partner_prefs


def _peer_project_preferences(
    desired_partners: list[int], project_preferences_so_far: list[tuple[int, ...]]
) -> tuple[list[int], ...]:
    available_prefs = [
        project_preferences_so_far[desired_partner]
        for desired_partner in desired_partners
        if desired_partner < len(project_preferences_so_far)
    ]
    return tuple(
        list(preferences_for_project) for preferences_for_project in zip(*available_prefs)
    )


def _peer_influenced_project_preference(preferences_for_project: list[int]) -> int:
    return max(preferences_for_project) if random.random() <= 0.5 else min(preferences_for_project)


def _random_project_preferences(
    num_projects: int,
    everyones_partner_preferences: list[list[int]],
    percentage_peer_influenced: float,
    min_pref: int,
    max_pref: int,
) -> list[tuple[int, ...]]:
    project_preferences_per_student: list[tuple[int, ...]] = []
    for partner_preferences in everyones_partner_preferences:
        peer_preferences_per_project = _peer_project_preferences(
            partner_preferences, project_preferences_per_student
        )
        if peer_preferences_per_project:
            student_project_preferences = tuple(
                (
                    _peer_influenced_project_preference(peer_preferences_for_project)
                    if random.random() <= percentage_peer_influenced
                    else random.randint(min_pref, max_pref)
                )
                for peer_preferences_for_project in peer_preferences_per_project
            )
        else:
            student_project_preferences = tuple(
                random.randint(min_pref, max_pref) for _ in range(num_projects)
            )

        project_preferences_per_student.append(student_project_preferences)

    return project_preferences_per_student


def random_students_df(
    num_projects: int,
    num_students: int,
    min_num_partner_preferences: int,
    max_num_partner_preferences: int,
    percentage_reciprocity: float,
    percentage_peer_influenced_project_preferences: float,
    min_project_preference: int,
    max_project_preference: int,
) -> pandas.DataFrame:
    """Returns random specifications for a given number of students.

    Args:
        num_projects: The number of projects.
        num_students: The number of students.

        min_num_partner_preferences: The minimum number of peers any student specifies as those
            he/she would like to work with.
        max_num_partner_preferences: The maximum...

        percentage_reciprocity: Roughly the "probability" of reciprocating a partner preference.
            The partner preferences are generated for one student after another. If at the time at
            which the partner preferences for a given student are generated that student has
            already been specified by another student, this is the probability with which the
            student will reciprocate it. Unless more other students have specified the student
            than his/her number of partner preferences. Then this probability only applies to a
            random sample where the size equals the student's number of partner preferences.

        percentage_peer_influenced_project_preferences: The "probability" that a project preference
            of the student is that of one of his/her preferred partners that have already specified
            their project preferences (project preferences are created subsequently student after
            student). If the preference is influenced by peers it is the maximum or minimum
            preference value among the peers with a 50/50 chance.

        min_project_preference: The lowest possible project preference.
        max_project_preference: The highest...

    Returns:
        For all students the project preference for every project and their preferred partners
        i.e., the students each student wants to work with. THE INDEX POSITION IN THE DATAFRAME
        IS THE STUDENT'S ID.
    """
    partner_preferences = _random_partner_preferences(
        num_students,
        percentage_reciprocity,
        min_num_partner_preferences,
        max_num_partner_preferences,
    )
    project_preferences = _random_project_preferences(
        num_projects,
        partner_preferences,
        percentage_peer_influenced_project_preferences,
        min_project_preference,
        max_project_preference,
    )

    return pandas.DataFrame(
        {
            "fav_partners": partner_preferences,
            "project_prefs": project_preferences,
        }
    )

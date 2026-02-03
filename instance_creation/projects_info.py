"""Create random specifications for a given number of projects.

These encompass constraints, wishes and penalties regarding the number of groups which are
supervised as well as the size of each group.
"""

import random

import pandas


def random_projects_df(
    num_projects: int,
    min_desired_num_groups: int,
    max_desired_num_groups: int,
    min_manageable_surplus_groups: int,
    max_manageable_surplus_groups: int,
    min_ideal_group_size: int,
    max_ideal_group_size: int,
    min_tolerable_group_size_deficit: int,
    max_tolerable_group_size_deficit: int,
    min_tolerable_group_size_surplus: int,
    max_tolerable_group_size_surplus: int,
    min_pen_num_groups: int,
    max_pen_num_groups: int,
    min_pen_group_size: int,
    max_pen_group_size: int,
) -> pandas.DataFrame:
    """Return random specifications for a given number of projects.

    The arguments serve as boundaries in between which random values are created.

    Args:
        num_projects: The number of projects in the instance.

        min_desired_num_groups: The minimum number of groups any project wishes to supervise.
        max_desired_num_groups: The maximum...

        min_manageable_surplus_groups: The minimum number of groups any project is ready to
            supervise on top of those it whishes to supervise.
        max_manageable_surplus_groups: The maximum...

        min_ideal_group_size: The minimum group size any project deems ideal.
        max_ideal_group_size: The maximum...

        min_tolerable_group_size_deficit: The minimum negative deviation from the ideal group size
            any project accepts.
        max_tolerable_group_size_deficit: The maximum...
        min_tolerable_group_size_surplus: The minimum positive deviation...
        max_tolerable_group_size_surplus: The maximum...

        min_pen_num_groups: The minimum penalty for each group exceeding the number of groups the
            project whishes to supervise. This random penalty is specific to each project.
        max_pen_num_groups: The maximum...

        min_pen_group_size: The minimum coefficient with which deviation from ideal_group_size is
            penalized. The random coefficient is specific to each project.
        max_pen_group_size: The maximum...

        Returns:
            Each project's constraints, whishes and penalties regarding the number of groups and
            group sizes. THE INDEX POSITION IN THE DATAFRAME IS THE PROJECT'S ID.
    """

    desired_nums_groups = [
        random.randint(min_desired_num_groups, max_desired_num_groups) for _ in range(num_projects)
    ]
    max_nums_groups = [
        desired_num_groups
        + random.randint(min_manageable_surplus_groups, max_manageable_surplus_groups)
        for desired_num_groups in desired_nums_groups
    ]
    ideal_group_sizes = [
        random.randint(min_ideal_group_size, max_ideal_group_size) for _ in range(num_projects)
    ]
    min_group_sizes = [
        max(
            1,
            ideal_group_size
            - random.randint(
                min_tolerable_group_size_deficit,
                max_tolerable_group_size_deficit,
            ),
        )
        for ideal_group_size in ideal_group_sizes
    ]
    max_group_sizes = [
        ideal_group_size
        + random.randint(min_tolerable_group_size_surplus, max_tolerable_group_size_surplus)
        for ideal_group_size in ideal_group_sizes
    ]
    pen_num_groups = [
        random.randint(min_pen_num_groups, max_pen_num_groups) for _ in range(num_projects)
    ]
    pen_group_size = [
        random.randint(min_pen_group_size, max_pen_group_size) for _ in range(num_projects)
    ]

    data_projects = {
        "desired#groups": desired_nums_groups,
        "max#groups": max_nums_groups,
        "ideal_group_size": ideal_group_sizes,
        "min_group_size": min_group_sizes,
        "max_group_size": max_group_sizes,
        "pen_groups": pen_num_groups,
        "pen_size": pen_group_size,
    }

    return pandas.DataFrame(data_projects)

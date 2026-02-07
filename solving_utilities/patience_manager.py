"""Class that manages the patience per subproblem for each number of zones."""

import itertools


class PatienceManager:
    """Manages the patience per subproblem for each number of zones.

    What is the point?
    If there are less zones, each zone has more assignments in it, which leads to bigger
    subproblems. This begs the question of how much time should be spent on larger subproblems
    compared to the time spent on smaller ones.

    An approach on how to split the time in optimization:
    At the same time, the number of possible pairs decreases with the number of zones. E.g. with 4
    zones there are 6 pairs and with 3 zones 3 pairs. It seems somewhat reasonable to spent an
    equal amount of time per number of zones e.g. if 1 minute is spent per subproblem with 4
    zones, 2 minutes are spent per subproblem with 3 zones.

    How this idea is mapped to the concept of patience:
    If we replace the time spent per subproblem with patience, there is the benefit of staying
    longer in a solution space in which an improvement was found. Therefore if the patience is 1
    minute for 4 zones, it is 2 minutes for 3 zones.

    This increase in patience as the number of zones decreases is rather conservative. Otherwise,
    if the difficulty would not increase more dramatically with the amount of assignments that are
    free, what would be the point of solving subproblems at all?

    How patience is adjusted:
    If for all pairs of a number of zones no improvement was found, the patience will be increased
    by a certain "step" for the next time for each of those pairs. This step is defined by the user
    for the maximum number of zones as min_patience_step. The step for lower number of zones is
    min_patience_step * max_num_pairs / num_pairs, where max_num_pairs is the number of pairs
    for the the maximum number of zones.

    Further, it is made sure that the sum of patiences over all pairs is non-decreasing as the
    number of zones gets lower. E.g. the patience per pair was 1 minute per pair for 4 zones and no
    improvement was found. For the next time, the patience per pair is increased by a step of 10s.
    The sum of patiences for 4 zones is now 7m. If the sum of patiences for 3 zones is below 7m,
    it will be increased to 7m, before any of the 3 pairs is searched. This can be seen as a mild
    counterweight to the overall rather conservative increase in patience as the number of zones
    decreases.

    Args:
        min_num_zones: The minimum number of zones
        max_num_zones: The maximum...
        min_patience: The minimum patience per pair i.e. the patience per pair for max_num_zones
            before any increases.
        min_patience_step: The step in patience per pair for max_num_zones.
    """

    def __init__(
        self,
        min_num_zones: int,
        max_num_zones: int,
        min_patience: float | int,
        min_patience_step: float | int,
    ):
        self._nums_zones = range(max_num_zones, min_num_zones - 1, -1)
        self._nums_pairs = {
            num_zones: len(list(itertools.combinations(range(num_zones), 2)))
            for num_zones in self._nums_zones
        }
        max_num_pairs = self._nums_pairs[max_num_zones]
        base_sum_patience_all_pairs = min_patience * max_num_pairs
        self.patiences = {
            num_zones: base_sum_patience_all_pairs / num_pairs
            for num_zones, num_pairs in self._nums_pairs.items()
        }
        self._patience_steps = {
            num_zones: min_patience_step * max_num_pairs / num_pairs
            for num_zones, num_pairs in self._nums_pairs.items()
        }

    def _ensure_non_decreasing_sums_of_patiences(self) -> None:
        for greater_num_zones, lesser_num_zones in itertools.pairwise(self._nums_zones):
            sum_patience_smaller_problems = (
                self.patiences[greater_num_zones] * self._nums_pairs[greater_num_zones]
            )
            sum_patience_larger_problems = (
                self.patiences[lesser_num_zones] * self._nums_pairs[lesser_num_zones]
            )

            self.patiences[lesser_num_zones] = (
                max(sum_patience_smaller_problems, sum_patience_larger_problems)
                / self._nums_pairs[lesser_num_zones]
            )

    def adjust_patiences(self, current_num_zones: int) -> None:
        """Increase the patience patience per pair for the given number of zones.

        If necessary also increase the the patience per pair for lower numbers of zones so that
        their sum of patiences over all pairs is not lower than that for the current number of
        zones.
        """
        self.patiences[current_num_zones] += self._patience_steps[current_num_zones]

        self._ensure_non_decreasing_sums_of_patiences()

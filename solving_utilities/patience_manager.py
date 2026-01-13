import itertools


class PatienceManager:

    def __init__(
        self,
        min_num_zones: int,
        max_num_zones: int,
        min_patience: float | int,
        min_patience_step: float | int,
    ):
        nums_zones = range(max_num_zones, min_num_zones - 1, -1)
        self.nums_pairs = {
            num_zones: len(list(itertools.combinations(range(num_zones), 2)))
            for num_zones in nums_zones
        }
        max_num_pairs = self.nums_pairs[max_num_zones]
        base_sum_patience_all_pairs = min_patience * max_num_pairs
        self.patiences = {
            num_zones: base_sum_patience_all_pairs / num_pairs
            for num_zones, num_pairs in self.nums_pairs.items()
        }
        self.patience_steps = {
            num_zones: min_patience_step * max_num_pairs / num_pairs
            for num_zones, num_pairs in self.nums_pairs.items()
        }

    def _align_patiences(self):
        for greater_num_zones, lesser_num_zones in itertools.pairwise(self.patiences.keys()):
            sum_patience_smaller_problems = (
                self.patiences[greater_num_zones] * self.nums_pairs[greater_num_zones]
            )
            sum_patience_larger_problems = (
                self.patiences[lesser_num_zones] * self.nums_pairs[lesser_num_zones]
            )

            self.patiences[lesser_num_zones] = (
                max(sum_patience_smaller_problems, sum_patience_larger_problems)
                / self.nums_pairs[lesser_num_zones]
            )

    def adjust_patience(self, current_num_zones: int):
        self.patiences[current_num_zones] += self.patience_steps[current_num_zones]

        self._align_patiences()

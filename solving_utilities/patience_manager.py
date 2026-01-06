import itertools
import statistics

import gurobipy


class PatienceManager:

    def __init__(
        self,
        model: gurobipy.Model,
        min_num_zones: int,
        max_num_zones: int,
        min_patience: float | int,
        base_patience_adjustment_rate: float,
    ):
        self.model = model
        self.base_adjustment_rate = base_patience_adjustment_rate
        nums_zones = range(max_num_zones, min_num_zones - 1, -1)
        self.num_pairs = {
            num_zones: len(list(itertools.combinations(range(num_zones), 2)))
            for num_zones in nums_zones
        }
        base_sum_patience_all_pairs = min_patience * self.num_pairs[max_num_zones]
        self.sum_patiences = dict.fromkeys(nums_zones, base_sum_patience_all_pairs)

        self.gap_vals_current_num_zones: list[float] = []
        self.num_unsuccessful_cycles = 0

    @property
    def adjustment_rate(self):
        return (1 + self.num_unsuccessful_cycles) * self.base_adjustment_rate

    def patience(self, num_zones: int) -> float:
        return self.sum_patiences[num_zones] / self.num_pairs[num_zones]

    def record_gap(self):
        self.gap_vals_current_num_zones.append(self.model.MIPGap)

    def clear_gap_vals(self):
        self.gap_vals_current_num_zones.clear()

    def _align_patiences(self):
        for greater_num_zones, lesser_num_zones in itertools.pairwise(self.sum_patiences.keys()):
            patience_smaller_zones = self.sum_patiences[greater_num_zones]
            patience_bigger_zones = self.sum_patiences[lesser_num_zones]
            self.sum_patiences[lesser_num_zones] = max(
                patience_smaller_zones, patience_bigger_zones
            )

    def adjust_patience(self, current_num_zones: int):
        if not self.gap_vals_current_num_zones:
            return
        if statistics.mean(self.gap_vals_current_num_zones) < 1e-4:
            self.sum_patiences[current_num_zones] *= 1 - self.adjustment_rate
        else:
            self.sum_patiences[current_num_zones] *= 1 + self.adjustment_rate

        self._align_patiences()

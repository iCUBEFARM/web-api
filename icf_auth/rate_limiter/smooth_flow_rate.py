from datetime import time


class SmoothFlowRate:
    def __init__(self, unit=60):
        self.last_count = 0
        self.cur_count = 0
        self.cur_ts = 0
        self.cur_bucket = 0
        self.unit = unit

    def __str__(self):
        return '{}(ts = {}, bucket = {}, last = {}, curr = {})'.format(
            __class__.__name__, self.cur_ts, self.cur_bucket,
            self.last_count, self.cur_count)

    def update(self, inc=1):
        now = int(time.time())
        bucket = now // self.unit

        if self.cur_bucket == 0:
            self.cur_bucket = bucket
        elif self.cur_bucket < (bucket - 1):
            self.last_count = 0
            self.cur_count = 0
        elif self.cur_bucket == (bucket - 1):
            self.last_count = self.cur_count
            self.cur_count = 0

        self.cur_ts = now
        self.cur_bucket = bucket
        self.cur_count += inc

        last_ratio = (self.cur_ts % self.unit) / self.unit
        smooth_count = (1 - last_ratio) * self.last_count + self.cur_count
        rate = smooth_count/self.unit  # per seconds
        return rate
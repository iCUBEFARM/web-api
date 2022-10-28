from datetime import time


class NaiveFlowRate:

    def __init__(self, unit=60):
        self.cur_count = 0
        self.cur_ts = 0
        self.cur_bucket = 0
        self.unit = unit

    def __str__(self):
        return '{}(ts = {}, bucket = {}, curr = {})'.format(
            __class__.__name__, self.cur_ts, self.cur_bucket, self.cur_count)

    def update(self, inc=1):
        # now = int(current_timestamp())
        now = int(time.time())
        bucket = now // self.unit
        if bucket != self.cur_bucket:
            self.cur_count = 0
            self.cur_bucket = bucket
        self.cur_ts = now
        self.cur_count += inc

        rate = self.cur_count / self.unit
        return rate
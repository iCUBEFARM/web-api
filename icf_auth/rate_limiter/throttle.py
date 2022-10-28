from datetime import time
from random import random


class Throttle(object):
    def __init__(self, rate_limit, flow_rate):
        self.rate_limit = rate_limit
        self.flow_rate = flow_rate

    def _wait_once(self, rate):
        if not self.rate_limit or rate < self.rate_limit:
            return 0
        delay = self.flow_rate.unit * (rate - self.rate_limit) / self.rate_limit
        if delay > 0.1:
            time.sleep(delay + random.random() * 0.5)
            return delay
        return 0

    def get_rate(self, precision=2):
        return round(self.flow_rate.update(0), precision)

    def _wait(self):
        res = 0
        while True:
            rate = self.get_rate()
            v = self._wait_once(rate)
            res += v
            if v == 0:
                break
        return res

    def run(self, inc=1):
        res = self._wait()
        rate = self.flow_rate.update(inc)
        return res + self._wait_once(rate)

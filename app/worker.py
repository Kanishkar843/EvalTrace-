"""One bounded worker; jobs survive process death and are reclaimed after lease expiry."""

import argparse, time
from .engine import Engine

p = argparse.ArgumentParser()
p.add_argument("--once", action="store_true")
a = p.parse_args()
e = Engine()
while True:
    result = e.work_one()
    if a.once:
        break
    if result is None:
        time.sleep(1)

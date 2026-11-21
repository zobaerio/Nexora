"""Deterministic, stateless RNG streams.

Every random draw in the simulation comes from a stream keyed by
(seed, context...). The stream is a pure function of its key, so:
- the same seed always produces the same simulation (byte-identical
  summaries across runs), and
- save/restore needs no RNG state: closing and reopening the database
  cannot change any future draw.

No module in this package may import `random` directly except through
this file, and nothing may use time, os.urandom or hash() of str
(PYTHONHASHSEED-dependent) for simulation decisions.
"""
import hashlib
import random


class SimRng:
    def __init__(self, seed):
        self.seed = str(seed)

    def stream(self, *context):
        """A random.Random keyed deterministically by the context."""
        key = "|".join([self.seed] + [str(c) for c in context])
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return random.Random(int.from_bytes(digest[:8], "big"))

    def for_agent_day(self, character_id, day_index, purpose):
        return self.stream("agent", character_id, "day", day_index, purpose)

    def for_day(self, day_index, purpose):
        return self.stream("world", "day", day_index, purpose)

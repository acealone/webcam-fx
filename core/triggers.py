"""Gesture -> effect triggers with a hold time and a re-arm lock."""


class Trigger:
    def __init__(self, gesture: str, effect: str, hold: float, rearm: float):
        self.gesture, self.effect, self.hold, self.rearm = gesture, effect, hold, rearm
        self.locked = False           # after firing: wait until the gesture is gone for `rearm` seconds
        self._held_since = None
        self._released_since = None

    def reset_hold(self):
        self._held_since = None

    def update(self, present: bool, now: float) -> bool:
        """Feed one frame. Returns True when the trigger fires."""
        if self.locked:   # one missed detection doesn't unlock: absence must last `rearm` s in a row
            self._released_since = None if present else (now if self._released_since is None else self._released_since)
            self.locked = self._released_since is None or now - self._released_since < self.rearm
            present = False
        if not present:
            self._held_since = None
            return False
        if self._held_since is None:
            self._held_since = now
        if now - self._held_since >= self.hold:
            self.locked, self._held_since, self._released_since = True, None, None
            return True
        return False


def fire_first(triggers: list, presence: list, now: float):
    """Update triggers in order; the first one that fires wins and the others restart their hold."""
    for trig, present in zip(triggers, presence):
        if trig.update(present, now):
            for other in triggers:
                if other is not trig:
                    other.reset_hold()
            return trig
    return None

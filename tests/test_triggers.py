from core.triggers import Trigger, fire_first

DT = 1 / 30


class Clock:
    t = 0.0


def run(trigger, seconds, fn, clock):
    """Feed `fn(frame_index) -> present` at 30 fps; return the times the trigger fired."""
    fired = []
    for i in range(round(seconds / DT)):
        if trigger.update(fn(i), clock.t):
            fired.append(clock.t)
        clock.t += DT
    return fired


def test_rearm_sequence():
    trig, clock = Trigger("g", "e", hold=0.3, rearm=0.5), Clock()
    first = run(trig, 1.0, lambda i: True, clock)
    assert len(first) == 1 and 0.29 < first[0] < 0.37
    assert run(trig, 3.0, lambda i: True, clock) == []                 # still held after the effect
    assert run(trig, 3.0, lambda i: i % 5 != 0, clock) == []           # flickering detection
    assert run(trig, 0.3, lambda i: False, clock) == [] and trig.locked
    assert run(trig, 1.0, lambda i: True, clock) == []                 # released too briefly
    assert run(trig, 0.7, lambda i: False, clock) == [] and trig.locked is False
    assert len(run(trig, 1.0, lambda i: True, clock)) == 1


def test_short_hold_does_not_fire():
    assert run(Trigger("g", "e", 0.3, 0.5), 0.2, lambda i: True, Clock()) == []


def test_missed_frame_restarts_hold():
    pattern = [True] * 8 + [False] + [True] * 8
    assert run(Trigger("g", "e", 0.3, 0.5), len(pattern) * DT, lambda i: pattern[i], Clock()) == []


def test_first_matching_trigger_wins():
    a, b = Trigger("ga", "ea", 0.3, 0.5), Trigger("gb", "eb", 0.3, 0.5)
    t, winner = 0.0, None
    while winner is None:
        winner = fire_first([a, b], [True, True], t)
        t += DT
    assert winner is a
    for _ in range(round(0.2 / DT)):                                    # b's hold restarted at a's fire
        assert fire_first([a, b], [True, True], t) is None
        t += DT
    assert not b.locked

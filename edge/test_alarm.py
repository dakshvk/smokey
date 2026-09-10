'''Proves the streaming alarm implements the same rule validated on FIgLib.

The equivalence test is the important one: without it, an off-by-one here means
the deployed system behaves differently from the benchmark in the writeup.
'''
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'eval'))

from edge.alarm import CameraAlarm, AlarmBank
from figlib_eval import fires


def test_matches_offline_fires():
    '''THE test: streaming hot-ness must equal figlib_eval.fires() at every frame.'''
    random.seed(0)
    for trial in range(200):
        K = random.randint(1, 4)
        M = K + random.randint(0, 4)
        th = random.choice([0.2, 0.4, 0.56, 0.8])
        confs = [random.random() for _ in range(random.randint(1, 60))]

        a = CameraAlarm(th, K, M)
        for i, c in enumerate(confs):
            a.update(c)
            expected = fires(confs, i, th, K, M)
            assert a.hot == expected, (
                f'trial {trial} frame {i}: K={K} M={M} th={th} '
                f'streaming={a.hot} offline={expected}')


def test_fires_once_while_sustained():
    '''A 40-minute plume is one alarm, not 40.'''
    a = CameraAlarm(0.5, 1, 1)
    edges = [a.update(0.9) for _ in range(40)]
    assert sum(edges) == 1, f'expected 1 alarm, got {sum(edges)}'
    assert edges[0] is True


def test_rearms_after_going_cold():
    a = CameraAlarm(0.5, 1, 1)
    assert a.update(0.9) is True     # fires
    assert a.update(0.9) is False    # still hot
    assert a.update(0.1) is False    # cold, re-arms
    assert a.update(0.9) is True     # fires again


def test_k_of_m_tolerates_a_gap():
    '''2 of the last 3 - they need not be consecutive.'''
    a = CameraAlarm(0.5, 2, 3)
    assert a.update(0.9) is False    # 1 hot, need 2
    assert a.update(0.1) is False    # still 1
    assert a.update(0.9) is True     # 2 of last 3, with a gap between


def test_window_never_grows():
    a = CameraAlarm(0.5, 1, 4)
    for _ in range(10_000):
        a.update(random.random())
    assert len(a._window) == 4


def test_consecutive_required_when_k_equals_m():
    a = CameraAlarm(0.5, 3, 3)
    for c in (0.9, 0.9, 0.1):
        a.update(c)
    assert a.hot is False            # a gap breaks it
    for c in (0.9, 0.9, 0.9):
        a.update(c)
    assert a.hot is True


def test_bank_keeps_cameras_independent():
    b = AlarmBank(0.5, 1, 1)
    assert b.update('cam-a', 0.9) is True
    assert b.update('cam-b', 0.1) is False    # a's alarm doesn't leak into b
    assert b.hot_cameras() == ['cam-a']


def test_rejects_bad_k_m():
    for K, M in ((0, 3), (4, 3), (-1, 1)):
        try:
            CameraAlarm(0.5, K, M)
        except ValueError:
            continue
        raise AssertionError(f'K={K} M={M} should have raised')


if __name__ == '__main__':
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_')]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f'ok    {name}')
        except AssertionError as e:
            failed += 1
            print(f'FAIL  {name}: {e}')
    print(f'\n{len(tests) - failed}/{len(tests)} passed')
    sys.exit(1 if failed else 0)
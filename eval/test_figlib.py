'''
Tests for figlib_eval. No model, no images, no GPU -- every function under test
is arithmetic over numbers we choose, so we know the right answer in advance.

Run from the repo root:   python eval/test_figlib.py
'''

import os
import tempfile

from figlib_eval import (parse_offset, load_sequence, fires, score_sequence,
                         sweep, operating_point)


def test_parse_offset():
    assert parse_offset('1465063200_-02400.jpg') == -2400
    assert parse_offset('1465068000_+02400.jpg') == 2400
    assert parse_offset('1465065600_+00000.jpg') == 0
    # leading zeros and both signs must survive int()


def test_fires_window():
    confs = [0.9, 0.1, 0.9, 0.9, 0.9]

    # K=1: any single hot frame in the window
    assert fires(confs, 0, 0.6, K=1, M=1) is True
    assert fires(confs, 1, 0.6, K=1, M=1) is False

    # K=3 consecutive: frames 2,3,4 are hot, so it trips at index 4 only
    assert fires(confs, 3, 0.6, K=3, M=3) is False   # only 2 hot so far
    assert fires(confs, 4, 0.6, K=3, M=3) is True

    # 3-of-5 tolerates the cold frame at index 1
    assert fires(confs, 4, 0.6, K=3, M=5) is True


def test_fires_early_frames_do_not_wrap():
    '''
    The negative-index trap. At i=0 with M=5 the naive slice start is -4, and a
    negative index reads from the END of the list instead of clamping. If max(0,..)
    is missing this reads the last 4 frames and wrongly returns True.
    '''
    confs = [0.1, 0.1, 0.1, 0.9, 0.9, 0.9]
    assert fires(confs, 0, 0.6, K=1, M=5) is False


def test_clean_detection():
    frames = [(-300, 0.1), (-240, 0.1), (-180, 0.1), (-120, 0.1), (-60, 0.1),
              (   0, 0.2), (  60, 0.9), ( 120, 0.9), ( 180, 0.9), ( 240, 0.9)]

    # K=3 needs three hot frames: +60, +120, +180 -> completes at +180
    r = score_sequence(frames, 0.6, K=3, M=3)
    assert r['detect_offset'] == 180, r
    assert r['false_alarms'] == 0, r

    # K=1 has no latency floor
    r = score_sequence(frames, 0.6, K=1, M=1)
    assert r['detect_offset'] == 60, r


def test_persistence_suppresses_a_spike():
    '''The entire point of the K knob, in one test.'''
    spike = [(-300, 0.1), (-240, 0.9), (-180, 0.9), (-120, 0.1), (-60, 0.1),
             (   0, 0.2), (  60, 0.9), ( 120, 0.9), ( 180, 0.9), ( 240, 0.9)]

    assert score_sequence(spike, 0.6, K=1, M=1)['false_alarms'] == 1
    assert score_sequence(spike, 0.6, K=3, M=3)['false_alarms'] == 0


def test_alarm_events_not_frames():
    '''A sustained run is ONE alarm. Two separated runs are TWO.'''
    one_run = [(-300, 0.9), (-240, 0.9), (-180, 0.9), (-120, 0.9), (-60, 0.9)]
    assert score_sequence(one_run, 0.6, K=1, M=1)['false_alarms'] == 1

    two_runs = [(-300, 0.9), (-240, 0.1), (-180, 0.9), (-120, 0.1), (-60, 0.9)]
    assert score_sequence(two_runs, 0.6, K=1, M=1)['false_alarms'] == 3
    # hot, cold, hot, cold, hot -> re-arms between each -> 3 events


def test_never_detected_is_none():
    quiet = [(-60, 0.1), (0, 0.1), (60, 0.1), (120, 0.1)]
    assert score_sequence(quiet, 0.6, K=1, M=1)['detect_offset'] is None


def test_operating_point_rejects_low_detect_rate():
    '''
    The fast-but-useless row must lose. It detects 1 fire in 10 and does it in
    1 minute; the honest row catches 95% in 4 minutes. Without the detect_rate
    floor, min() on time picks the broken one.
    '''
    rows = [
        {'thresh': 0.9, 'K': 1, 'M': 1, 'alarms_per_day': 0.1,
         'detect_rate': 0.10, 'median_ttd_min': 1.0},
        {'thresh': 0.5, 'K': 3, 'M': 5, 'alarms_per_day': 0.5,
         'detect_rate': 0.95, 'median_ttd_min': 4.0},
    ]
    best = operating_point(rows, max_alarms_per_day=1.0, min_detect_rate=0.9)
    assert best['thresh'] == 0.5, best


def test_operating_point_returns_none_when_nothing_fits():
    rows = [{'thresh': 0.5, 'K': 1, 'M': 1, 'alarms_per_day': 50.0,
             'detect_rate': 0.99, 'median_ttd_min': 2.0}]
    assert operating_point(rows, max_alarms_per_day=1.0) is None



# ---------------------------------------------------------------------------
# Coverage for load_sequence and sweep -- the two functions the original tests
# never called. A green suite only tells you the TESTED code works.
# ---------------------------------------------------------------------------

def test_load_sequence_reads_every_frame():
    '''
    Builds a throwaway folder so the test needs no downloaded data.
    Catches the classic bug where sort()/return sit INSIDE the for loop, which
    makes the function return after the very first .jpg.
    '''
    with tempfile.TemporaryDirectory() as d:
        # tempfile.TemporaryDirectory() deletes the whole folder on exit, so
        # the test leaves nothing behind even if it fails partway through
        for off in (-120, -60, 0, 60, 120):
            sign = '+' if off >= 0 else '-'
            name = f'1465063200_{sign}{abs(off):05d}.jpg'   # -> '1465063200_-00120.jpg'
            open(os.path.join(d, name), 'w').close()        # empty file; only the name matters
        open(os.path.join(d, 'sequence.mp4'), 'w').close()  # must be ignored

        frames = load_sequence(d)

        assert len(frames) == 5, f'expected 5 frames, got {len(frames)}'
        # os.listdir returns arbitrary order, so this also proves the sort ran
        assert [o for o, _ in frames] == [-120, -60, 0, 60, 120], frames


def test_sweep_actually_sweeps_thresholds():
    '''
    Catches [1/100 for i in ...] where i is never used -- that yields 99 copies
    of 0.01, so the sweep silently tests a single threshold.
    '''
    frames = [(-120, 0.1), (-60, 0.1), (0, 0.2), (60, 0.9), (120, 0.9)]
    rows = sweep([frames])

    distinct = {r['thresh'] for r in rows}        # set comprehension de-duplicates
    assert len(distinct) == 99, f'expected 99 distinct thresholds, got {len(distinct)}'
    assert min(distinct) == 0.01, min(distinct)
    assert max(distinct) == 0.99, max(distinct)


def test_alarms_per_day_uses_1440_minutes():
    '''
    10 fire-free minutes containing exactly 1 alarm event.
    1 alarm / (10/1440 of a day) = 144.0 alarms per day.
    A 1140 typo gives 114.0 instead -- wrong by 26%, and silent.
    '''
    frames = [(-600, 0.9)] + [(-540 + 60 * i, 0.1) for i in range(9)]
    # 10 frames, all pre-ignition, only the first is hot

    rows = sweep([frames], thresholds=[0.6], Ks=(1,), M_extra=(0,))
    # pin every knob so exactly one row comes back and the arithmetic is exact
    assert len(rows) == 1, rows
    assert rows[0]['alarms_per_day'] == 144.0, rows[0]


def test_sweep_row_count_matches_grid():
    '''thresholds x Ks x M_extra -- guards against a dropped loop level.'''
    frames = [(-60, 0.1), (0, 0.2), (60, 0.9)]
    rows = sweep([frames], thresholds=[0.3, 0.6], Ks=(1, 2), M_extra=(0, 1))
    assert len(rows) == 2 * 2 * 2, len(rows)
    assert {r['M'] - r['K'] for r in rows} == {0, 1}


if __name__ == '__main__':
    # collect every function in this file whose name starts with test_
    tests = [v for k, v in sorted(globals().items())
             if k.startswith('test_') and callable(v)]
    # globals() is a dict of every name defined at module level, so this finds
    # the tests without listing them by hand -- add a new one and it just runs

    failed = 0
    for t in tests:
        try:
            t()
            print(f'  PASS  {t.__name__}')
        except AssertionError as e:
            failed += 1
            print(f'  FAIL  {t.__name__}: {e}')
    print(f'\n{len(tests) - failed}/{len(tests)} passed')
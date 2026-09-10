'''Proves the outbox never loses a detection.'''
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from edge.outbox import Outbox


def fresh():
    return Outbox(os.path.join(tempfile.mkdtemp(), 'test.db'))


def test_survives_process_death():
    '''The whole point: close the handle, reopen, everything is still pending.'''
    path = os.path.join(tempfile.mkdtemp(), 'crash.db')
    ob = Outbox(path)
    ids = [ob.add('cam-a', '2026-09-09T12:00:00Z', 0.9) for _ in range(5)]
    ob.close()                       # simulates the process dying

    ob2 = Outbox(path)               # reboot
    pending = ob2.pending(100)
    assert len(pending) == 5, f'lost rows: {len(pending)}/5 survived'
    assert {r['id'] for r in pending} == set(ids)


def test_failure_keeps_it_pending():
    ob = fresh()
    i = ob.add('cam-a', '2026-09-09T12:00:00Z', 0.9)
    for _ in range(10):
        ob.mark_failed(i, 'connection refused')
    assert len(ob.pending()) == 1, 'a failed send must never drop the row'


def test_sent_rows_leave_the_queue():
    ob = fresh()
    i = ob.add('cam-a', '2026-09-09T12:00:00Z', 0.9)
    ob.mark_sent(i)
    assert ob.pending() == []
    assert ob.stats().get('sent') == 1


def test_ids_are_unique():
    '''Idempotency depends on this - a repeat id would deduplicate a real alert.'''
    ob = fresh()
    ids = {ob.add('cam-a', '2026-09-09T12:00:00Z', 0.9) for _ in range(500)}
    assert len(ids) == 500


def test_oldest_first():
    ob = fresh()
    a = ob.add('cam-a', '2026-09-09T12:00:00Z', 0.9)
    b = ob.add('cam-b', '2026-09-09T12:01:00Z', 0.9)
    assert [r['id'] for r in ob.pending()] == [a, b]


def test_trim_never_drops_pending():
    '''A long outage must not silently discard unsent work.'''
    ob = Outbox(os.path.join(tempfile.mkdtemp(), 't.db'), max_rows=10)
    sent = [ob.add('c', '2026-09-09T12:00:00Z', 0.5) for _ in range(10)]
    for i in sent:
        ob.mark_sent(i)
    for _ in range(10):
        ob.add('c', '2026-09-09T12:00:00Z', 0.9)      # forces trimming
    assert len(ob.pending(100)) == 10, 'pending rows were trimmed away'


def test_bbox_roundtrip():
    ob = fresh()
    i = ob.add('cam-a', '2026-09-09T12:00:00Z', 0.9, bbox=[1, 2, 3, 4])
    assert ob.pending()[0]['bbox'] == '[1, 2, 3, 4]'


if __name__ == '__main__':
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_')]
    failed = 0
    for name, fn in tests:
        try:
            fn(); print(f'ok    {name}')
        except AssertionError as e:
            failed += 1; print(f'FAIL  {name}: {e}')
    print(f'\n{len(tests) - failed}/{len(tests)} passed')
    sys.exit(1 if failed else 0)
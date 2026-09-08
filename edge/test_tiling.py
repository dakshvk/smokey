import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from edge.tiling import tile_grid

def test_every_tile_is_full_size():
    for x0, y0, x1, y1 in tile_grid(3072, 2048, tile=1024, overlap=128):
        assert x1 - x0 == 1024 and y1 - y0 == 1024

def test_no_tile_leaves_the_image():
    for x0, y0, x1, y1 in tile_grid(3072, 2048):
        assert 0 <= x0 < x1 <= 3072
        assert 0 <= y0 < y1 <= 2048

def test_full_coverage():
    '''every pixel lands in at least one tile'''
    W, H = 3072, 2048
    tiles = tile_grid(W, H, tile=1024, overlap=128)
    covered = [[False]*(W//64) for _ in range(H//64)]   # 64px sampling grid
    for x0, y0, x1, y1 in tiles:
        for r in range(y0//64, y1//64):
            for c in range(x0//64, x1//64):
                covered[r][c] = True
    assert all(all(row) for row in covered)

def test_tiles_actually_overlap():
    tiles = tile_grid(3072, 2048, tile=1024, overlap=128)
    xs = sorted({t[0] for t in tiles})
    assert all(b - a <= 1024 - 128 for a, b in zip(xs, xs[1:]))

def test_image_smaller_than_tile():
    '''a 640x480 image should still produce one usable tile'''
    tiles = tile_grid(640, 480, tile=1024, overlap=128)
    assert len(tiles) == 1

if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn(); print(f'ok  {name}')
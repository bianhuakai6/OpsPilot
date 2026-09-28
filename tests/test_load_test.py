from scripts.load_test import percentile


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([40, 10, 30, 20], 50) == 20
    assert percentile([40, 10, 30, 20], 95) == 40
    assert percentile([], 95) == 0

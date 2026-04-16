from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_representative_ribo_fixtures_remain_present() -> None:
    symlink_fixtures = (
        ROOT / "tests" / "test_data" / "GSE102659_all.ribo",
        ROOT / "tests" / "test_data" / "GSE105082_all.ribo",
    )
    for path in symlink_fixtures:
        assert path.is_symlink(), f"Expected fixture symlink to remain intact: {path}"

    binary_fixtures = (
        ROOT / "tests" / "test_data" / "GSE106448.ribo",
        ROOT / "tests" / "test_data" / "all.ribo",
    )
    for path in binary_fixtures:
        assert path.exists(), f"Expected fixture file to exist: {path}"
        assert path.stat().st_size > 0, f"Expected fixture file to be non-empty: {path}"

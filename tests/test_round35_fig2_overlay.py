from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts import plot_round35_fig2_h12_overlay


def _write_pair(tmp_path: Path, stem: str, h_value: int, scale: float) -> tuple[Path, Path, Path]:
    snr = [13.5, 13.55, 13.6]
    ref = tmp_path / f"{stem}_ref.csv"
    lut = tmp_path / f"{stem}_lut.csv"
    diff = tmp_path / f"{stem}_diff.csv"
    common = {
        "snr_db": snr,
        "h": [h_value] * len(snr),
        "post_fec_errors": [100, 80, 60],
        "post_fec_ber": [1e-2 * scale, 5e-3 * scale, 1e-3 * scale],
        "total_bits": [10_000_000] * len(snr),
    }
    pd.DataFrame({**common, "backend": ["syndrome_lut"] * len(snr)}).to_csv(ref, index=False)
    pd.DataFrame({**common, "backend": ["block_lut"] * len(snr), "block_width": [14] * len(snr)}).to_csv(
        lut, index=False
    )
    pd.DataFrame(
        {
            "snr_db": snr,
            "matched": [True] * len(snr),
            "post_fec_errors_delta": [0] * len(snr),
            "post_fec_ber_delta": [0.0] * len(snr),
        }
    ).to_csv(diff, index=False)
    return ref, lut, diff


def test_round35_fig2_overlay_writes_outputs(tmp_path: Path) -> None:
    h16_ref, h16_lut, h16_diff = _write_pair(tmp_path, "h16", 16, 1.0)
    h12_ref, h12_lut, h12_diff = _write_pair(tmp_path, "h12", 12, 2.0)
    out_dir = tmp_path / "figures"

    assert (
        plot_round35_fig2_h12_overlay.main(
            [
                "--h16-reference-csv",
                str(h16_ref),
                "--h16-block-lut-csv",
                str(h16_lut),
                "--h16-diff-csv",
                str(h16_diff),
                "--h12-reference-csv",
                str(h12_ref),
                "--h12-block-lut-csv",
                str(h12_lut),
                "--h12-diff-csv",
                str(h12_diff),
                "--output-dir",
                str(out_dir),
                "--output-stem",
                "overlay_smoke",
            ]
        )
        == 0
    )

    assert (out_dir / "overlay_smoke.png").exists()
    assert (out_dir / "overlay_smoke.pdf").exists()

"""Correctness-test skeleton for bit-exact backend comparisons."""


def test_package_imports() -> None:
    from linear_kernel import (  # noqa: F401
        BlockLUTKernel,
        EventUpdateKernel,
        HybridPlanner,
        NaiveGF2Kernel,
        PackedBatchGF2Kernel,
        SparseXorKernel,
    )

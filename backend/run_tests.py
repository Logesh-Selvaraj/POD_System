import os
import sys
import time
import pytest

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["USE_SQLITE"] = "true"

test_files = [
    "tests/test_auth.py",
    "tests/test_deliveries.py",
    "tests/test_dispatcher.py",
    "tests/test_quality_engine.py",
    "tests/test_relationships.py",
    "tests/test_admin.py",
    "tests/test_experiments.py",
    "tests/test_validation.py",
    "tests/test_e2e_scenarios.py"
]

print("--- RUNNING BACKEND TESTS ---")
failed_suites = []
for tf in test_files:
    t0 = time.time()
    ret = pytest.main(["-v", tf])
    t1 = time.time()
    print(f"[{tf}] Result: {ret} in {t1-t0:.2f}s")
    if ret != 0:
        failed_suites.append(tf)

if failed_suites:
    print(f"\n[FAIL] Test suites failed: {failed_suites}")
    sys.exit(1)
else:
    print("\n[SUCCESS] All backend test suites passed successfully!")
    sys.exit(0)

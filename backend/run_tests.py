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
    "tests/test_relationships.py"
]

print("--- RUNNING BACKEND TESTS ---")
for tf in test_files:
    t0 = time.time()
    ret = pytest.main(["-v", tf])
    t1 = time.time()
    print(f"[{tf}] Result: {ret} in {t1-t0:.2f}s")

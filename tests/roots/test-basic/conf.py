import os
import sys

# `sphinx.testing` copies a doc root to a temp directory before building, so
# __file__ points at the copy and relative paths to the repo resolve to nothing.
# tests/conftest.py passes the repository location in through the environment;
# the fallback is for running sphinx-build against the checked-in root directly.
_REPO = os.environ.get("DVFLOW_TEST_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".."))

sys.path.insert(0, os.path.join(_REPO, "src"))

extensions = ["sphinx_dv_flow"]
dvflow_root = os.path.join(_REPO, "tests", "data", "simple")
exclude_patterns = ["_build"]

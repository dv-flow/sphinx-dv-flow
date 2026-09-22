# Markdown prose WITH `myst_parser` enabled -- the documented upgrade path,
# where myst itself does the parsing rather than the built-in conversion.
import os
import sys

_REPO = os.environ.get("DVFLOW_TEST_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".."))

sys.path.insert(0, os.path.join(_REPO, "src"))

extensions = ["myst_parser", "sphinx_dv_flow"]
dvflow_root = os.path.join(_REPO, "tests", "data", "markdown")
dvflow_doc_format = "markdown"
exclude_patterns = ["_build"]

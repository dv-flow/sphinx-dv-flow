# Markdown prose WITHOUT `myst_parser` in `extensions`.
#
# This is the configuration that was broken: with myst-parser merely installed
# -- a dependency of something else, or this package's `markdown` extra -- the
# renderer reached myst's Sphinx parser, which reads its configuration from
# `env.myst_config`. That attribute is attached by myst_parser's own `setup()`,
# so it does not exist here, and the resulting AttributeError fell through to
# the reStructuredText parser. Well-formed Markdown then produced docutils
# errors located in the flow file.
import os
import sys

_REPO = os.environ.get("DVFLOW_TEST_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".."))

sys.path.insert(0, os.path.join(_REPO, "src"))

extensions = ["sphinx_dv_flow"]
dvflow_root = os.path.join(_REPO, "tests", "data", "markdown")
dvflow_doc_format = "markdown"
exclude_patterns = ["_build"]

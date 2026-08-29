# Configuration file for the Sphinx documentation builder.
#
# These docs are also the acceptance test for the extension: every directive
# sphinx-dv-flow ships is used here, against the fixture packages under
# `tests/data`, and CI builds this tree with `-W`. A directive that produces a
# warning is a directive that is not done.

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "sphinx-dv-flow"
copyright = "2025, Matthew Ballance"
author = "Matthew Ballance"

extensions = [
    "sphinxcontrib.mermaid",
    # The extension documents itself. This is not a convenience: it means a
    # change that breaks the extension breaks its own docs build.
    "sphinx_dv_flow",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

nitpicky = True

html_theme = "furo"
html_static_path = ["_static"]

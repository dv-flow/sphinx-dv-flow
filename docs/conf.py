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

# Every reference these pages generate now resolves. M1 needed a
# `nitpick_ignore_regex` for `dvf:type`, because the dataflow blocks emitted
# type references before the directive that registers type targets existed;
# M2's `dvf:autotype` removed the need for it.
#
# The one thing this requires of `example.rst`: a package rendered with
# `:types:` must document its tasks too, or the "Produced by" links on the type
# pages point at tasks no page describes. That is nitpicky doing its job -- the
# reference really is dangling -- so the fix belongs in the document, not here.
nitpicky = True

# `std` is a different distribution, and this doc set does not document it --
# so a fixture type extending `std.Check` produces a reference with nowhere to
# land. That is a real situation for any project building on a library, and the
# real answer is intersphinx (M5), which resolves such names against the other
# project's inventory. Until then it is silenced narrowly, by package prefix:
# a dangling reference to anything in *this* project still fails the build.
nitpick_ignore_regex = [
    (r'dvf:.*', r'std\..*'),
]

html_theme = "furo"
html_static_path = ["_static"]

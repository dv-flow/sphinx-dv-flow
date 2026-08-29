"""Make the source tree importable without requiring an install.

ivpm's virtualenv has no pip, so `pip install -e .` is not available in the
development environment or in CI. Putting `src` on the path here means the
suite runs from a plain checkout.

`PYTHONPATH` is updated as well as `sys.path`, because some tests re-enter
Python in a subprocess -- notably the guard that checks `dv_flow.doc` never
imports Sphinx, which *must* run out-of-process to mean anything (pytest has
already imported Sphinx by then, so an in-process check would pass regardless).
A subprocess inherits the environment, not our `sys.path`.
"""

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

_existing = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing.split(os.pathsep):
    os.environ["PYTHONPATH"] = (
        _SRC + os.pathsep + _existing) if _existing else _SRC

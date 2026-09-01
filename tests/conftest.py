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

import pytest

# Sphinx's own test fixtures (`app`, `make_app`, `warning`, ...). They drive a
# real build, which is the only way to test a directive: the interesting
# failures -- an unpicklable environment, a domain that loses objects across a
# parallel read -- happen in the build machinery, not in the node construction.
pytest_plugins = ['sphinx.testing.fixtures']

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

_existing = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing.split(os.pathsep):
    os.environ["PYTHONPATH"] = (
        _SRC + os.pathsep + _existing) if _existing else _SRC

# `sphinx.testing` copies each doc root to a temp directory before building it,
# so a `conf.py` cannot find the repository from its own `__file__`. Passing the
# location through the environment is the only thing that survives the copy.
os.environ["DVFLOW_TEST_ROOT"] = _ROOT


def pytest_addoption(parser):
    parser.addoption(
        "--update-golden", action="store_true", default=False,
        help="Rewrite golden files from the current extraction. Review the "
             "diff: a golden updated without anyone reading the change has "
             "stopped being a test.")


@pytest.fixture(scope="session")
def data_dir():
    """Directory holding the fixture flow packages."""
    return os.path.join(_ROOT, "tests", "data")


@pytest.fixture(scope="session")
def golden_dir():
    return os.path.join(_ROOT, "tests", "golden")


@pytest.fixture(scope="session")
def loaded(data_dir):
    """`{fixture-name: LoadResult}`, loaded once for the whole session.

    Session-scoped because loading is the expensive part and these fixtures are
    read-only. A test that mutates a loaded package would corrupt every later
    test, so don't -- extraction is a pure function over the model, and there is
    no reason to.
    """
    from dv_flow.doc.loader import load_project

    out = {}
    for name in ("simple", "library", "inherit", "types", "abstract",
                 "lifecycle"):
        result = load_project(os.path.join(data_dir, name))
        assert result.ok, "fixture %s failed to load: %s" % (
            name, [m.msg for m in result.markers])
        # A fixture that emits diagnostics is a broken fixture: every test
        # downstream would be reasoning about a project the engine complained
        # about.
        assert [m.msg for m in result.markers] == [], (
            "fixture %s produced markers" % name)
        out[name] = result
    return out


@pytest.fixture(scope="session")
def rootdir():
    """Where `@pytest.mark.sphinx(testroot=...)` looks for doc roots.

    Sphinx resolves `testroot='basic'` to `rootdir / 'test-basic'`.
    """
    from pathlib import Path
    return Path(_ROOT) / "tests" / "roots"

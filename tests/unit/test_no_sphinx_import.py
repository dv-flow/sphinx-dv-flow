"""Ground rule 1: `dv_flow.doc` does not depend on Sphinx.

This is the one decision in the project that is expensive to reverse. A single
convenience import -- a docutils node type, a Sphinx logger, `sphinx.util.osutil`
-- pulls Sphinx into the extractor's import graph, and once it is there, every
later module is free to assume it. So the rule is checked mechanically, from the
first commit, rather than trusted.

Two things ride on it. `dfm` may consume the extractor without acquiring a
Sphinx dependency, and the extraction contract stays inspectable as plain data
without standing up a Sphinx build.

The check runs in a subprocess. It has to: pytest has already imported Sphinx
by the time these tests run (the build tests use `sphinx.testing`), so an
in-process `sys.modules` check would pass no matter what `dv_flow.doc` imports.
"""

import json
import pkgutil
import subprocess
import sys
import textwrap

import pytest


# Modules whose presence means the rule is broken. `docutils` is included
# because it is Sphinx's document model: an extractor that builds docutils
# nodes is a renderer, whatever it imports.
FORBIDDEN = ("sphinx", "docutils")


PROBE = textwrap.dedent("""\
    import importlib, json, pkgutil, sys

    import dv_flow.doc

    # Walk every submodule, not just the package root. `dv_flow.doc/__init__.py`
    # is deliberately thin, so importing only it would prove nothing about the
    # modules that hold the actual code.
    failures = {}
    names = ["dv_flow.doc"] + [
        m.name for m in pkgutil.walk_packages(
            dv_flow.doc.__path__, prefix="dv_flow.doc.")]

    for name in names:
        before = set(sys.modules)
        try:
            importlib.import_module(name)
        except Exception as e:
            failures.setdefault("import_errors", []).append(
                "%s: %s: %s" % (name, type(e).__name__, e))
            continue
        # Attribute a forbidden module to the first import that pulled it in,
        # which is the one worth reporting -- everything after it inherits the
        # already-loaded module and looks innocent.
        for forbidden in __FORBIDDEN__:
            landed = [m for m in set(sys.modules) - before
                      if m == forbidden or m.startswith(forbidden + ".")]
            if landed:
                failures.setdefault("sphinx_imports", []).append(
                    "%s pulled in %s" % (name, ", ".join(sorted(landed))))

    print(json.dumps({"names": names, "failures": failures}))
""").replace("__FORBIDDEN__", repr(FORBIDDEN))


@pytest.fixture(scope="module")
def probe():
    proc = subprocess.run(
        [sys.executable, "-c", PROBE],
        capture_output=True, text=True)
    assert proc.returncode == 0, (
        "probe subprocess failed:\n%s\n%s" % (proc.stdout, proc.stderr))
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_no_submodule_imports_sphinx(probe):
    failures = probe["failures"].get("sphinx_imports", [])
    assert failures == [], (
        "dv_flow.doc must not import Sphinx or docutils:\n  " +
        "\n  ".join(failures))


def test_every_submodule_imports_cleanly(probe):
    """A module that fails to import is also a module the guard cannot check."""
    failures = probe["failures"].get("import_errors", [])
    assert failures == [], "\n  ".join([""] + failures)


def test_the_walk_actually_found_modules(probe):
    """Guard the guard.

    If the walk ever returns just the package root -- a renamed directory, a
    packaging change that drops `__path__` -- both tests above pass while
    checking nothing. This test fails instead.
    """
    assert len(probe["names"]) > 1, (
        "walk found only %r; the guard is not inspecting any submodules"
        % (probe["names"],))


def test_sphinx_dv_flow_does_import_sphinx_lazily():
    """The rendering layer is allowed Sphinx -- but need not import it eagerly.

    `sphinx_dv_flow` is loaded by Sphinx itself, so this is not a rule, just a
    record of current behavior: importing the extension package does not by
    itself pull in the world. If that changes deliberately, update this test;
    it is here so the change is deliberate.
    """
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sphinx_dv_flow, sys; print('sphinx' in sys.modules)"],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"

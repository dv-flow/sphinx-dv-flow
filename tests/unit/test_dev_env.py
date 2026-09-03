"""`ivpm update -a` must select a dep-set that installs something.

ivpm picks the dep-set to install in this order (``ivpm/project_ops.py``,
``_getDepSet``): the ``-d`` argument, then ``default-dep-set:``, then **the
first dep-set in the file**. This project's first dep-set is ``use``, which is
deliberately empty -- so without ``default-dep-set:`` the bare command installs
nothing, *exits zero*, and creates no virtualenv.

That is why this is a test. The command succeeds, so nothing downstream of it
reports the real cause: CI failed two steps later with
``./packages/python/bin/pytest: No such file or directory``, and it went
unnoticed locally because a populated ``packages/`` already existed from an
earlier explicit ``-d dev``. Only a clean checkout takes the default path.

``docs/install.rst`` documents the bare command, so this guards what a new
contributor actually types, not just CI.
"""

import os
import re

import pytest

yaml = pytest.importorskip("yaml")

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

IVPM_YAML = os.path.join(_ROOT, "ivpm.yaml")
GH_WORKFLOW = os.path.join(_ROOT, ".github", "workflows", "ci.yml")
INSTALL_DOC = os.path.join(_ROOT, "docs", "install.rst")


def _package():
    with open(IVPM_YAML, encoding="utf-8") as fp:
        return yaml.safe_load(fp)["package"]


def _dep_sets():
    return {ds["name"]: (ds.get("deps") or []) for ds in _package()["dep-sets"]}


def test_the_default_dep_set_is_named_and_not_empty():
    pkg = _package()
    dep_sets = _dep_sets()

    default = pkg.get("default-dep-set")
    assert default, (
        "ivpm.yaml declares no default-dep-set, so `ivpm update -a` falls back "
        "to the first dep-set in the file")
    assert default in dep_sets, default
    assert dep_sets[default], (
        "the default dep-set %r is empty; `ivpm update -a` would install "
        "nothing and still exit 0" % default)


def test_the_default_dep_set_provides_what_ci_then_runs():
    """pytest and sphinx are what the next two CI steps invoke."""
    default = _package().get("default-dep-set")
    assert default in _dep_sets(), (
        "no usable default-dep-set; see the failure above for why")
    deps = {d["name"] for d in _dep_sets()[default]}

    assert {"pytest", "sphinx", "dv-flow-mgr"} <= deps, sorted(deps)


def test_ci_checks_the_environment_before_using_it():
    """The step that turns a silent zero-install into a named failure."""
    workflow = _read(GH_WORKFLOW)

    assert "The dev environment must actually exist" in workflow
    assert "installed nothing" in workflow


def test_ci_runs_the_command_the_docs_document():
    """If CI passed `-d dev` and the docs said `ivpm update -a`, the documented
    command could break with nothing to notice."""
    assert re.search(r"^\s*run: ivpm update -a\s*$", _read(GH_WORKFLOW), re.M)
    assert "ivpm update -a" in _read(INSTALL_DOC)


def _read(path):
    with open(path, encoding="utf-8") as fp:
        return fp.read()

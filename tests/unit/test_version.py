"""The version is written down once, and the release job can find it.

None of this is testing Python behaviour -- it is testing a contract between
three files that no import touches: `src/dv_flow/doc/__version__.py` holds the
number, `pyproject.toml` reads it, and `.github/workflows/ci.yml` rewrites part
of it with `sed` at build time.

That last one is why these are tests rather than comments. `sed` succeeds when
its pattern matches nothing, so renaming `SUFFIX` or moving the file produces a
*green* release build that stamped nothing at all. dv-flow-mgr's Forgejo
workflow exists largely to catch this class of failure and records four repos in
the org already in that state; the damage is only visible on PyPI, after the
version can no longer be reused.

The Forgejo job checks the same contract in CI. It is duplicated here on
purpose: a check that only runs on a forge is a check that nobody sees before
pushing.
"""

import importlib
import os
import re


def _version_module():
    """The `__version__` *module*, not the string of the same name.

    `dv_flow.doc.__init__` does `from .__version__ import __version__`, which
    rebinds the attribute on the package from the submodule to the string it
    exported. So `from dv_flow.doc import __version__` gets a `str`, and
    `import_module` is the only way to reach the module itself.
    """
    return importlib.import_module("dv_flow.doc.__version__")


_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

VERSION_FILE = os.path.join(_ROOT, "src", "dv_flow", "doc", "__version__.py")
PYPROJECT = os.path.join(_ROOT, "pyproject.toml")
GH_WORKFLOW = os.path.join(_ROOT, ".github", "workflows", "ci.yml")
FJ_WORKFLOW = os.path.join(_ROOT, ".forgejo", "workflows", "ci.yml")


def _read(path):
    with open(path, encoding="utf-8") as fp:
        return fp.read()


def test_the_module_reports_version_plus_suffix():
    version_mod = _version_module()

    assert version_mod.__version__ == version_mod.VERSION + version_mod.SUFFIX
    assert version_mod._pkg_version == version_mod.__version__


def test_the_package_exports_the_same_version():
    """`dv_flow.doc.__version__` must be the module's number, not metadata.

    Reading it from `importlib.metadata` -- which is what this package used to
    do -- reports whatever was last installed into the environment, so a
    checkout under test happily claims the version of a wheel built weeks ago.
    """
    import dv_flow.doc
    version_mod = _version_module()

    assert dv_flow.doc.__version__ == version_mod.__version__

    import sphinx_dv_flow
    assert sphinx_dv_flow.__version__ == version_mod.__version__


def test_the_version_is_a_release_number_in_the_source_tree():
    """SUFFIX is empty until CI sets it.

    A committed suffix would be published as part of the next release: the tag
    build clears it, but only by matching a pattern, and a hand-edited value is
    exactly the case where someone has also been editing patterns.
    """
    version_mod = _version_module()

    assert version_mod.SUFFIX == ""
    assert re.match(r"^\d+\.\d+\.\d+$", version_mod.VERSION), version_mod.VERSION


def test_the_literals_have_the_shape_the_release_job_rewrites():
    """The `sed` in the release job anchors on these exact lines."""
    text = _read(VERSION_FILE)

    assert re.search(r'^VERSION = "[^"]+"$', text, re.M)
    assert re.search(r'^SUFFIX = "[^"]*"$', text, re.M)


def test_the_release_job_stamps_this_file():
    """Nothing in Python breaks if the file moves; only this notices."""
    workflow = _read(GH_WORKFLOW)
    assert "src/dv_flow/doc/__version__.py" in workflow

    # And it must guard the substitution, because a `sed` that matched nothing
    # is otherwise indistinguishable from a successful stamp.
    assert 'grep -qE \'^SUFFIX = "\'' in workflow


def test_the_release_job_only_publishes_from_a_tag_and_with_authority():
    """Two conditions, both required, on the one step that reaches PyPI.

    A push to a branch must never publish: this repo is in a bidirectional
    Forgejo<->GitHub mirror, and a mirror push to `main` is indistinguishable
    from a human one. Losing either half of the condition is a one-character
    edit that no other check would catch.
    """
    workflow = _read(GH_WORKFLOW)

    publish = workflow.split("Publish to PyPI", 1)[1]
    condition = re.search(r"^\s*if: (.*)$", publish, re.M).group(1)

    assert "refs/tags/v" in condition
    assert "needs.gate.outputs.authority == 'github'" in condition


def test_there_is_exactly_one_copy_of_the_version():
    """A literal in pyproject.toml is what lets `pip show` and `import` differ."""
    text = _read(PYPROJECT)

    assert re.search(r'^\s*dynamic\s*=.*"version"', text, re.M)
    assert 'version = {attr = "dv_flow.doc.__version__._pkg_version"}' in text
    assert not re.search(r'^\s*version\s*=\s*"', text, re.M)


def test_both_forges_have_a_workflow():
    """Forgejo falls back to running `.github/workflows/` when `.forgejo/` is
    absent -- which would mean a second forge executing this repo's release
    path, on the same tags, with a run-ID counter that is not GitHub's.
    """
    assert os.path.exists(GH_WORKFLOW)
    assert os.path.exists(FJ_WORKFLOW)

    # The Forgejo side must not acquire a publish step: the release-authority
    # switch resolves this repo to `github`, and PYPI_API_TOKEN is a GitHub org
    # secret. Both agree today; this is what keeps them agreeing.
    assert "twine upload" not in _read(FJ_WORKFLOW)

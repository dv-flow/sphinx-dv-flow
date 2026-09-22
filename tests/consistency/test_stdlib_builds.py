"""The standard library documents itself (design §12.1, PLAN M6).

`std` is the first real package this extension was pointed at, and it is a
harder target than any fixture: several dozen tasks and types, 8 filters, prose
written in Markdown, and a package whose types are the vocabulary every other
flow file speaks.

This builds a documentation set over the *installed* `std` and asserts the
result under `-W`. It is deliberately not a copy of dv-flow-mgr's whole doc
tree -- that build takes half a minute and most of it is unrelated to this
extension. What is pinned here is the part that would break: extraction and
rendering of a real package.

WHAT IS PINNED, AND WHAT IS NOT. `std` belongs to dv-flow-mgr and grows on its
own schedule, so the assertions below name the objects they expect and check
containment. An exact count would make this repo's CI go red on a commit to
another repo that did nothing wrong -- which is what it did when `std` gained a
14th task. A DROP is still caught, and caught by name rather than by arithmetic.
"""

import importlib.util
import os

import pytest


def _find_std():
    """Locate the installed `std` package directory.

    From the module rather than from a path relative to this repo. The old
    form looked for `packages/dv-flow-mgr/...` under the repo root, which
    exists only when the checkout is the top of an ivpm tree -- so for anyone
    whose sphinx-dv-flow lives *inside* someone else's `packages/`, every test
    in this file skipped. Five silent skips is how a stale assertion reached
    CI: the suite was green locally and had simply not run them.
    """
    spec = importlib.util.find_spec("dv_flow.mgr")
    if spec is None or not spec.submodule_search_locations:
        return None
    return os.path.join(list(spec.submodule_search_locations)[0], "std")


STD = _find_std()

pytestmark = pytest.mark.skipif(
    STD is None or not os.path.isfile(os.path.join(STD, "flow.yaml")),
    reason="dv_flow.mgr is not importable, so there is no std to build")

CONF = """\
import sys
sys.path.insert(0, %r)
extensions = ["sphinx_dv_flow"]
dvflow_root = %r
dvflow_doc_format = "markdown"
exclude_patterns = ["_build"]
"""

INDEX = """\
Standard Library
================

.. dvf:autopackage::
   :types:
"""


@pytest.fixture(scope="module")
def stdlib_docs(tmp_path_factory):
    src = tmp_path_factory.mktemp("stdlib")
    repo_src = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "src")
    (src / "conf.py").write_text(CONF % (repo_src, STD), encoding="utf-8")
    (src / "index.rst").write_text(INDEX, encoding="utf-8")
    return src


def _build(make_app, srcdir, **kw):
    app = make_app("html", srcdir=srcdir, freshenv=True, **kw)
    app.build()
    return app


def test_stdlib_builds_without_warnings(make_app, stdlib_docs):
    """The `-W` claim, against the real package.

    Markdown is what `std` is written in: `doc:` prose reaches `dfm show` and
    `dfm llms` as well as Sphinx, and fenced code blocks are what people type
    when the consumer is a terminal.
    """
    app = _build(make_app, stdlib_docs)
    assert app._warning.getvalue().strip() == ""


#: Every task `std` exported when this was last reviewed. Checked as a SUBSET,
#: so dv-flow-mgr adding a task does not fail this repo -- but dropping one from
#: the documented set still does, and says which.
EXPECTED_TASKS = {
    "std.Agent", "std.CreateFile", "std.FileSet", "std.IncDirs", "std.Message",
    "std.NotProvided", "std.Null", "std.PubSet", "std.Publish", "std.RunTasks",
    "std.SetEnv", "std.SetFileType", "std.TestInfo", "std.TestRunner",
}


def test_every_std_task_is_documented(make_app, stdlib_docs):
    """Every exported task, and none of them silently dropped.

    This is the assertion that caught the finding M6 existed to find: every
    `std` task was declared with a bare `name:` and no scope, which by the
    visibility model means package-internal -- so the first run of this
    documented **zero** tasks.
    """
    app = _build(make_app, stdlib_docs)
    tasks = {name for (objtype, name) in app.env.get_domain("dvf").objects
             if objtype == "task"}
    assert EXPECTED_TASKS - tasks == set()


def test_std_types_are_documented(make_app, stdlib_docs):
    app = _build(make_app, stdlib_docs)
    types = {name for (objtype, name) in app.env.get_domain("dvf").objects
             if objtype == "type"}
    assert "std.FileSet" in types
    assert "std.PubSet" in types


def test_std_filters_are_documented(make_app, stdlib_docs):
    """`std` keeps its filters in a fragment, which is exactly the case that
    would document none of them if extraction read the package file alone."""
    app = _build(make_app, stdlib_docs)
    filters = {name for (objtype, name) in app.env.get_domain("dvf").objects
               if objtype == "filter"}
    expected = {"std." + n for n in (
        "by_filetype", "by_type", "pluck", "first_of_type",
        "basenames", "extensions", "paths", "count_by_type")}
    assert expected - filters == set()


def test_markdown_prose_is_rendered_not_escaped(make_app, stdlib_docs):
    """`std.TestInfo` carries a fenced YAML block. Under `rst` it fails to
    parse; the point of `dvflow_doc_format` is that it does not have to."""
    app = _build(make_app, stdlib_docs)
    text = app.env.get_doctree("index").astext()
    assert "tests-info" in text
    assert "```" not in text

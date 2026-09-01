"""The standard library documents itself (design §12.1, PLAN M6).

`std` is the first real package this extension was pointed at, and it is a
harder target than any fixture: 13 tasks, 23 types, 8 filters, prose written in
Markdown, and a package whose types are the vocabulary every other flow file
speaks.

This builds a documentation set over the *installed* `std` and asserts the
result under `-W`. It is deliberately not a copy of dv-flow-mgr's whole doc
tree -- that build takes half a minute and most of it is unrelated to this
extension. What is pinned here is the part that would break: extraction and
rendering of a real package.
"""

import os

import pytest

STD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "packages", "dv-flow-mgr", "src", "dv_flow", "mgr", "std")

pytestmark = pytest.mark.skipif(
    not os.path.isfile(os.path.join(STD, "flow.yaml")),
    reason="dv-flow-mgr checkout not present")

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


def test_every_std_task_is_documented(make_app, stdlib_docs):
    """13 tasks, and none of them silently dropped.

    This is the assertion that caught the finding M6 existed to find: every
    `std` task was declared with a bare `name:` and no scope, which by the
    visibility model means package-internal -- so the first run of this
    documented **zero** tasks.
    """
    app = _build(make_app, stdlib_docs)
    tasks = {name for (objtype, name) in app.env.get_domain("dvf").objects
             if objtype == "task"}
    assert "std.Message" in tasks
    assert "std.FileSet" in tasks
    assert "std.Publish" in tasks
    assert len(tasks) == 13


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
    assert "std.by_filetype" in filters
    assert len(filters) == 8


def test_markdown_prose_is_rendered_not_escaped(make_app, stdlib_docs):
    """`std.TestInfo` carries a fenced YAML block. Under `rst` it fails to
    parse; the point of `dvflow_doc_format` is that it does not have to."""
    app = _build(make_app, stdlib_docs)
    text = app.env.get_doctree("index").astext()
    assert "tests-info" in text
    assert "```" not in text

"""The extractor and `dfm` must answer the same question the same way.

Ground rule §0.2. Every fact the extension shows comes from an engine contract
rather than being re-derived -- but "comes from" is an intention until something
checks it. These tests are that check: they compare the extracted document
against what `dfm show task` reports for the same task, so a divergence shows up
here rather than as documentation that quietly disagrees with the tool.

The failure this prevents is specifically the silent one. If the extractor
re-derived the option list and the engine later changed how flags inherit, the
docs would keep rendering the old answer and nothing would complain.
"""

import json
import os
import subprocess
import sys

import pytest

from dv_flow.doc.loader import load_project
from dv_flow.doc.task import extract_task


def _dfm(root, *args):
    """Run `dfm` as a subprocess and return parsed JSON.

    A subprocess, not an in-process call, because the point is to compare
    against what the *tool* reports -- including any wiring in its command
    layer. Importing the command class would skip exactly the part most likely
    to drift.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "dv_flow.mgr", "show", "task", *args, "--json"],
        cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip("dfm show task unavailable: %s" % proc.stderr.strip()[:200])
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def simple_root(request):
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "simple")


def test_usage_matches_dfm_show_task_usage(simple_root):
    """The option list is carried verbatim, so it must be identical.

    Not "equivalent" -- identical. `TaskDoc.usage` is `build_usage_info()`
    unmodified, and if that ever stops being true the two will drift in a way
    only a reader comparing the docs to `--help` would notice.
    """
    expected = _dfm(simple_root, "simple.run", "--usage")

    result = load_project(simple_root)
    doc = extract_task(result.pkg.task_m["simple.run"],
                       result.pkg, result.loader)

    # `default` may hold non-JSON-safe values on either side; compare through
    # the same serialization both consumers would apply.
    assert json.loads(json.dumps(doc.usage, default=str)) == expected


def test_params_match_dfm_show_task(simple_root):
    """Same parameter set, same defaults, as the detail view reports."""
    expected = _dfm(simple_root, "simple.run")

    result = load_project(simple_root)
    doc = extract_task(result.pkg.task_m["simple.run"],
                       result.pkg, result.loader)

    assert {p.name for p in doc.params} == set(expected["params"])

    for p in doc.params:
        assert str(p.default) == expected["param_values"][p.name], p.name


def test_desc_and_doc_match(simple_root):
    expected = _dfm(simple_root, "simple.run")
    result = load_project(simple_root)
    doc = extract_task(result.pkg.task_m["simple.run"],
                       result.pkg, result.loader)
    assert doc.desc == expected["desc"]
    assert doc.doc == expected["doc"]


def test_examples_match(simple_root):
    """The authored content of every example, as `dfm` reports it.

    Compared field by field rather than whole: `ExampleDoc` also carries where
    the example came from and whether it still loads, and neither is something
    `dfm show` knows or should. What has to agree is what the author wrote --
    which is the whole of ground rule 2's claim here.
    """
    expected = _dfm(simple_root, "simple.run")
    result = load_project(simple_root)
    doc = extract_task(result.pkg.task_m["simple.run"],
                       result.pkg, result.loader)
    authored = [{k: e.to_dict()[k]
                 for k in ("title", "code", "caption", "lang")}
                for e in doc.examples]
    assert authored == expected["examples"]


def test_tags_match(request):
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "library")
    expected = _dfm(root, "library.Retired")
    result = load_project(root)
    doc = extract_task(result.pkg.task_m["library.Retired"],
                       result.pkg, result.loader)
    assert [t.to_dict() for t in doc.tags] == expected["tags"]


def test_inherited_params_match_on_a_derived_task(request):
    """The case where re-deriving would most plausibly disagree."""
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "inherit")
    expected = _dfm(root, "inherit.Leaf")
    result = load_project(root)
    doc = extract_task(result.pkg.task_m["inherit.Leaf"],
                       result.pkg, result.loader)
    assert {p.name for p in doc.params} == set(expected["params"])
    for p in doc.params:
        assert str(p.default) == expected["param_values"][p.name], p.name


def _root_tasks():
    """Every runnable task in every fixture, as (root, name) pairs.

    Discovered rather than listed, so a fixture added later is covered without
    anyone remembering to add it here. That matters more than it looks: the
    guard is only as good as its coverage, and a hand-maintained list is
    exactly the thing that stops matching reality.
    """
    from dv_flow.doc.classify import classify

    base = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    out = []
    for entry in sorted(os.listdir(base)):
        root = os.path.join(base, entry)
        if not os.path.isdir(root):
            continue
        result = load_project(root)
        if not result.ok:
            continue
        for name, task in (result.pkg.task_m or {}).items():
            if classify(task) == 'root':
                out.append((root, name))
    return out


@pytest.mark.parametrize("root,name", _root_tasks(),
                         ids=lambda v: v if isinstance(v, str) and '/' not in v
                         else os.path.basename(str(v)))
def test_every_root_task_agrees_on_usage(root, name):
    """The `--usage` view, for every runnable task in every fixture.

    `simple.run` alone proves the wiring; this proves it holds across the
    shapes -- inherited flags, open value sets, a task whose parameters come
    from a package variable. A contract checked on one example is a contract
    checked on one example.
    """
    expected = _dfm(root, name, "--usage")

    result = load_project(root)
    doc = extract_task(result.pkg.task_m[name], result.pkg, result.loader)

    assert json.loads(json.dumps(doc.usage, default=str)) == expected

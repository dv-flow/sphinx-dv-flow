"""Golden tests for the extraction contract, plus the facts goldens can't pin.

Goldens cover the *shape* of the document -- every field, in order, for a whole
task -- which is what catches an accidental change to the contract. They are
poor at saying *why* a value matters, so the facts that would be silently wrong
rather than obviously different get their own named tests below.

Regenerate with `--update-golden` after reviewing the diff. That flag exists so
the goldens can be updated deliberately; a golden file rewritten without anyone
reading the change has stopped being a test.
"""

import json
import os

import pytest

from dv_flow.doc.export.json_ import dumps, to_jsonable
from dv_flow.doc.task import extract_task


GOLDEN_TASKS = [
    ("simple", "simple.run"),
    ("library", "library.Compile"),
    ("library", "library.Link"),
    ("library", "library.Publish"),
    ("library", "library.Retired"),
    ("inherit", "inherit.Leaf"),
]


def _extract(loaded, fixture, task_name, data_dir):
    result = loaded[fixture]
    doc = extract_task(result.pkg.task_m[task_name], result.pkg, result.loader)
    return to_jsonable(doc, base_dir=os.path.join(data_dir, fixture))


@pytest.mark.parametrize("fixture,task_name", GOLDEN_TASKS)
def test_golden(loaded, fixture, task_name, data_dir, golden_dir, request):
    actual = _extract(loaded, fixture, task_name, data_dir)
    path = os.path.join(golden_dir, "%s.json" % task_name)

    if request.config.getoption("--update-golden"):
        os.makedirs(golden_dir, exist_ok=True)
        with open(path, "w") as f:
            f.write(json.dumps(actual, indent=2) + "\n")
        pytest.skip("golden updated: %s" % os.path.basename(path))

    assert os.path.exists(path), (
        "missing golden %s -- run pytest --update-golden and review the diff"
        % path)
    with open(path) as f:
        expected = json.load(f)
    assert actual == expected


def test_goldens_are_stable_across_two_extractions(loaded, data_dir):
    """The document must be a function of the model and nothing else.

    Dict ordering that depends on hashing, or a value that carries a timestamp
    or an absolute path, would make the goldens fail intermittently -- the worst
    kind of test failure, because the usual response is to re-run it.
    """
    first = _extract(loaded, "simple", "simple.run", data_dir)
    second = _extract(loaded, "simple", "simple.run", data_dir)
    assert json.dumps(first) == json.dumps(second)


def test_paths_are_relativized(loaded, data_dir):
    """An absolute srcinfo path changes with the checkout location, which would
    fail every golden on another machine for a reason unrelated to the code."""
    doc = _extract(loaded, "simple", "simple.run", data_dir)
    assert doc["srcinfo"]["file"] == "flow.yaml"
    assert not os.path.isabs(doc["srcinfo"]["file"])


# --------------------------------------------- facts a golden states but
# --------------------------------------------- does not explain

def test_kind_and_scope(loaded):
    result = loaded["simple"]
    doc = extract_task(result.pkg.task_m["simple.run"], result.pkg, result.loader)
    assert doc.kind == "root"
    assert doc.scope == ["root"]


def test_usage_is_present_for_a_root_task(loaded):
    """Carried verbatim from `build_usage_info`, not rebuilt.

    Ground rule §0.2: `dfm show task --usage` and the rendered option list must
    answer the same question the same way. Two derivations of "what flags does
    this task have" would eventually disagree, with the docs being the half
    nobody notices is wrong.
    """
    result = loaded["simple"]
    doc = extract_task(result.pkg.task_m["simple.run"], result.pkg, result.loader)
    assert doc.usage is not None
    assert doc.usage["task"] == "simple.run"
    assert {a["param"] for a in doc.usage["args"]} == {
        p.name for p in doc.params}


def test_usage_is_absent_for_a_library_task(loaded):
    """A library task has no command line, and an empty usage block would
    invite a renderer to draw one."""
    result = loaded["library"]
    doc = extract_task(result.pkg.task_m["library.Compile"],
                       result.pkg, result.loader)
    assert doc.usage is None


def test_an_authored_consumes_is_marked_declared(loaded):
    result = loaded["library"]
    doc = extract_task(result.pkg.task_m["library.Compile"],
                       result.pkg, result.loader)
    assert doc.consumes_declared is True


def test_an_inherited_consumes_is_still_declared(loaded):
    """Link declares none of its own but inherits Compile's through `uses:`.

    An inherited declaration IS a declaration -- the reader is subject to that
    contract -- so rendering it as "not declared" would hide it.
    """
    result = loaded["library"]
    doc = extract_task(result.pkg.task_m["library.Link"],
                       result.pkg, result.loader)
    assert doc.consumes_declared is True


def test_an_undeclared_consumes_is_not_a_claim(loaded):
    """`consumes` is defaulted to All by the engine, so it cannot answer this
    itself -- and reading the default as an authored claim is what makes a
    dataflow contract vacuous (design §4.2)."""
    result = loaded["library"]
    doc = extract_task(result.pkg.task_m["library.Publish"],
                       result.pkg, result.loader)
    assert doc.consumes_declared is False
    assert doc.consumes is not None  # the engine's default is still reported


def test_consumes_none_is_a_claim(loaded):
    """"Declared: no inputs" must not read the same as "said nothing"."""
    result = loaded["library"]
    doc = extract_task(result.pkg.task_m["library.Report"],
                       result.pkg, result.loader)
    assert doc.consumes_declared is True
    assert "No" in str(doc.consumes)


def test_produces_splits_type_from_attributes(loaded):
    result = loaded["library"]
    doc = extract_task(result.pkg.task_m["library.Compile"],
                       result.pkg, result.loader)
    assert [p.type for p in doc.produces] == ["library.ObjFile"]
    assert doc.produces[0].attrs == {}


def test_tags_carry_their_parameters(loaded):
    """A resolved tag's `paramT` is an INSTANCE, not a class -- the parameters
    are already bound. Stringifying the tag would give a consumer a repr blob,
    making the lifecycle tags unreadable exactly where they matter."""
    result = loaded["library"]
    doc = extract_task(result.pkg.task_m["library.Retired"],
                       result.pkg, result.loader)
    assert [t.name for t in doc.tags] == ["std.Deprecated"]
    assert doc.tags[0].params["replacement"] == "library.Compile"
    assert doc.tags[0].params["since"] == "1.4"


def test_tags_do_not_inherit(loaded):
    """Link uses Compile, which is std.Stable. Link is not."""
    result = loaded["library"]
    doc = extract_task(result.pkg.task_m["library.Link"],
                       result.pkg, result.loader)
    assert doc.tags == []


def test_the_uses_chain_excludes_the_task_itself(loaded):
    """The chain renders as "built on ...", and a list whose first entry is
    the thing you are reading is noise."""
    result = loaded["inherit"]
    doc = extract_task(result.pkg.task_m["inherit.Leaf"],
                       result.pkg, result.loader)
    assert doc.uses_chain == ["inherit.Middle", "inherit.Base"]


def test_desc_and_doc_are_inherited(loaded):
    """Upstream U8. A task deriving from a described base is not blank."""
    result = loaded["inherit"]
    doc = extract_task(result.pkg.task_m["inherit.Leaf"],
                       result.pkg, result.loader)
    assert doc.desc == "The top of the chain"


def test_examples_are_extracted(loaded):
    result = loaded["simple"]
    doc = extract_task(result.pkg.task_m["simple.run"], result.pkg, result.loader)
    assert [e.title for e in doc.examples] == [
        "Run with defaults", "Pick a backend"]
    assert doc.examples[0].lang == "shell"


def test_examples_do_not_inherit(loaded):
    """An example names a specific task and specific parameters, so a base's
    example would show the reader something they cannot type (upstream U1)."""
    result = loaded["inherit"]
    doc = extract_task(result.pkg.task_m["inherit.Leaf"],
                       result.pkg, result.loader)
    assert doc.examples == []


def test_behavior_reports_only_what_was_set(loaded):
    """A table of engine defaults tells the reader nothing and crowds out the
    one row that does."""
    result = loaded["library"]
    doc = extract_task(result.pkg.task_m["library.Compile"],
                       result.pkg, result.loader)
    assert "max_failures" not in doc.behavior
    assert "run" not in doc.behavior


def test_the_document_is_json_serializable(loaded):
    """Everything, including engine enums that reach `consumes`/`passthrough`."""
    result = loaded["library"]
    for name in result.pkg.task_m:
        doc = extract_task(result.pkg.task_m[name], result.pkg, result.loader)
        json.loads(dumps(doc))


# ------------------------------------------------------- documented outputs

def test_produces_doc_is_separated_from_attributes(loaded):
    """`doc:` describes the artifact; it is not something to match on.

    The engine excludes it from matching and from evaluation, and extraction
    has to make the same split -- otherwise a renderer would present a task's
    prose as an attribute a consumer could require.
    """
    result = loaded["types"]
    doc = extract_task(result.pkg.task_m["types.Package"],
                       result.pkg, result.loader)
    entry = doc.produces[0]
    assert entry.type == "types.Report"
    assert entry.doc == "${{ task_rundir }}/summary.txt"
    assert entry.attrs == {}


def test_produces_doc_reaches_the_page_unevaluated(loaded):
    """The unresolved `${{ task_rundir }}` is the part that generalises.

    A resolved path would be true only on the machine that built the docs, and
    outside a run there is nothing for it to resolve to.
    """
    result = loaded["types"]
    doc = extract_task(result.pkg.task_m["types.Package"],
                       result.pkg, result.loader)
    assert "${{" in doc.produces[0].doc


def test_an_undocumented_output_has_empty_doc(loaded):
    """Absence stays absence -- the type alone is a complete declaration."""
    result = loaded["types"]
    doc = extract_task(result.pkg.task_m["types.Link"],
                       result.pkg, result.loader)
    assert doc.produces[0].type == "types.Image"
    assert doc.produces[0].doc == ""


def test_attributes_are_still_attributes(loaded):
    """The `doc:` exclusion must not swallow real attributes."""
    result = loaded["types"]
    doc = extract_task(result.pkg.task_m["types.CompileC"],
                       result.pkg, result.loader)
    assert doc.produces[0].attrs == {"arch": "x86"}

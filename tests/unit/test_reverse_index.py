"""The reverse indices.

Every relationship in a flow file points one way: a task says what it produces,
nothing says what produces a type. Those reverse directions are most of what a
reference reader wants -- "I have an ObjFile, what can take one?" -- so they
have to be built, and these tests are about building them without losing
information along the way.
"""

import pytest

from dv_flow.doc.indices import apply_to_type, build_index
from dv_flow.doc.loader import load_project
from dv_flow.doc.type import extract_type


@pytest.fixture(scope="module")
def types_project(request):
    import os
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "types")
    result = load_project(root)
    assert result.ok
    return result


@pytest.fixture(scope="module")
def index(types_project):
    return build_index(types_project.pkg)


# ------------------------------------------------------------- produced by

def test_multiple_producers_are_all_recorded(index):
    """The normal case. An index that kept only the last producer would answer
    "where does this come from" with a lie that looks like a fact."""
    assert index.produced_by['types.ObjFile'] == [
        'types.CompileC', 'types.CompileAsm']


def test_a_type_nobody_produces_is_absent_rather_than_empty(index):
    """`Artifact` is a base type: it is produced only as one of its subtypes.

    The distinction matters to `apply_to_type`, which turns a missing key into
    an empty list -- so the page can say "nothing produces this" rather than
    omitting the section and looking unfinished.
    """
    assert 'types.Artifact' not in index.produced_by


# ------------------------------------------------------------- consumed by

def test_consumers_are_recorded(index):
    assert index.consumed_by['types.ObjFile'] == ['types.Link', 'types.Package']


def test_an_attribute_qualified_requirement_is_kept_distinct(index):
    """`{type: ObjFile}` and `{type: ObjFile, arch: arm}` are different
    requirements, and the index has to say WHICH consumer asked for which.

    Recording the qualifier against the type alone would let a renderer label
    every edge into `ObjFile` with `arch=arm` -- stating a constraint `Link`
    never declared.
    """
    assert index.consumed_as['types.ObjFile'] == {'types.Package': 'arch=arm'}
    assert 'types.Link' not in index.consumed_as['types.ObjFile']


def test_a_dead_end_output_has_no_consumers(index):
    """Nothing consumes `Report`. That is worth being able to see."""
    assert 'types.Report' not in index.consumed_by
    assert index.produced_by['types.Report'] == ['types.Package']


def test_the_consumes_enum_forms_are_not_indexed(index):
    """`consumes: all` says nothing about any specific type.

    Recording it would put every task under every type, which is the same as
    recording nothing while looking like real data.
    """
    for consumers in index.consumed_by.values():
        assert 'types.CompileC' not in consumers


# ------------------------------------------------------------ type hierarchy

def test_direct_subtypes_are_recorded(index):
    assert index.derived_types['types.Artifact'] == [
        'types.ObjFile', 'types.Image']


def test_the_index_is_not_transitive(index):
    """Direct subtypes only. The closure is reconstructible from these, and is
    rarely what a reader wants first."""
    assert 'types.ObjFile' not in index.derived_types


# --------------------------------------------------------------- applied to

def test_applying_the_index_fills_the_type_document(types_project, index):
    doc = apply_to_type(
        extract_type(types_project.pkg.type_m['types.ObjFile'],
                     types_project.pkg),
        index)
    assert doc.produced_by == ['types.CompileC', 'types.CompileAsm']
    assert doc.consumed_by == ['types.Link', 'types.Package']
    assert doc.derived_by == []


def test_applying_the_index_to_an_unused_type_gives_empty_lists(
        types_project, index):
    doc = apply_to_type(
        extract_type(types_project.pkg.type_m['types.Report'],
                     types_project.pkg),
        index)
    assert doc.produced_by == ['types.Package']
    assert doc.consumed_by == []


# --------------------------------------------------------- implementations

def test_implementations_are_indexed(data_dir):
    """Nothing in the flow file answers "what derives from this" -- `uses:`
    points the other way -- and it is the most useful thing an extension point
    can tell a reader."""
    import os
    result = load_project(os.path.join(data_dir, "abstract"))
    index = build_index(result.pkg)
    assert index.implementations['abstract.Backend'] == [
        'abstract.Vlt', 'abstract.Vcs']


def test_a_task_deriving_from_nothing_is_not_an_implementation(data_dir):
    import os
    result = load_project(os.path.join(data_dir, "abstract"))
    index = build_index(result.pkg)
    for impls in index.implementations.values():
        assert 'abstract.Standalone' not in impls


# ---------------------------------------------------------------- tagged with

def test_tags_are_indexed(data_dir):
    import os
    result = load_project(os.path.join(data_dir, "lifecycle"))
    index = build_index(result.pkg)
    assert index.tagged_with['std.Deprecated'] == [
        'lifecycle.Retired', 'lifecycle.Abandoned', 'lifecycle.Elsewhere']


# ------------------------------------------------------------------ ordering

def test_entries_follow_declaration_order(index):
    """Stable, and matching the order the package page lists tasks in, so a
    reader moving between the two sees the same sequence."""
    assert index.produced_by['types.ObjFile'] == [
        'types.CompileC', 'types.CompileAsm']


def test_the_index_is_serializable(index):
    import json
    json.dumps(index.to_dict())

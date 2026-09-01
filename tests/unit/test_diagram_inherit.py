"""The inheritance diagram -- a UML class view (design §6.4).

The attribute compartment is the point of this diagram. A box listing every
inherited parameter would show the same list at four levels and say nothing;
listing only what each level *introduces* makes provenance spatial — a reader
sees at a glance where a knob came from.
"""

import os

import pytest

from dv_flow.doc.diagram import inherit
from dv_flow.doc.indices import build_index
from dv_flow.doc.loader import load_project


def _project(name):
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", name)
    result = load_project(root)
    assert result.ok
    return result


@pytest.fixture(scope="module")
def chain():
    return _project("inherit")


@pytest.fixture(scope="module")
def abstract():
    result = _project("abstract")
    return result, build_index(result.pkg)


@pytest.fixture(scope="module")
def types():
    result = _project("types")
    return result, build_index(result.pkg)


def _attrs(model, label):
    return [n.attributes for n in model.nodes if n.label == label][0]


# ----------------------------------------------------------- the hierarchy

def test_ancestors_are_drawn(chain):
    model = inherit.build(chain.pkg.task_m["inherit.Leaf"])
    assert [n.label for n in model.nodes] == [
        "inherit.Leaf", "inherit.Middle", "inherit.Base"]


def test_generalization_edges_point_at_the_base(chain):
    model = inherit.build(chain.pkg.task_m["inherit.Leaf"])
    kinds = {e.kind for e in model.edges}
    assert kinds == {"uses"}
    assert len(model.edges) == 2


# --------------------------------------------- the attribute compartment

def test_a_level_lists_only_what_it_introduces(chain):
    """Not the merged set. `from_base` belongs to Base, and repeating it on
    Middle and Leaf would make the diagram say nothing about provenance."""
    model = inherit.build(chain.pkg.task_m["inherit.Leaf"])
    assert _attrs(model, "inherit.Middle") == ["from_middle"]
    assert "from_base" in _attrs(model, "inherit.Base")
    assert "from_base" not in _attrs(model, "inherit.Leaf")


def test_a_changed_default_is_marked_as_an_override(chain):
    """The visual form of "this task changed one thing" -- the same statement
    the parameter table's provenance column makes in words."""
    assert "overridden = leaf-default" in _attrs(
        inherit.build(chain.pkg.task_m["inherit.Leaf"]), "inherit.Leaf")


def test_an_override_with_an_empty_value_is_still_marked(chain):
    """`flag_removed` is re-declared only to drop its flag.

    Rendering it bare would read as a fresh declaration at that level, which is
    the one thing this compartment exists to get right.
    """
    assert "flag_removed (override)" in _attrs(
        inherit.build(chain.pkg.task_m["inherit.Leaf"]), "inherit.Leaf")


def test_a_fresh_declaration_carries_no_marker(chain):
    assert "own" in _attrs(
        inherit.build(chain.pkg.task_m["inherit.Leaf"]), "inherit.Leaf")


# ------------------------------------------------------------- abstract

def test_an_abstract_level_is_flagged(abstract):
    """Italic in UML, and matching the abstract banner on the task's page."""
    result, index = abstract
    model = inherit.build(result.pkg.task_m["abstract.Backend"], index=index)
    node = [n for n in model.nodes if n.label == "abstract.Backend"][0]
    assert node.abstract is True


def test_a_concrete_level_is_not(abstract):
    result, index = abstract
    model = inherit.build(result.pkg.task_m["abstract.Vlt"], index=index)
    node = [n for n in model.nodes if n.label == "abstract.Vlt"][0]
    assert node.abstract is False


# ------------------------------------------------------------- requires

def test_requires_is_drawn_as_realization(abstract):
    result, index = abstract
    model = inherit.build(result.pkg.task_m["abstract.Backend"], index=index)
    realizations = [e for e in model.edges if e.kind == "requires"]
    assert len(realizations) == 1


def test_the_check_type_is_added_as_a_node(abstract):
    result, index = abstract
    model = inherit.build(result.pkg.task_m["abstract.Backend"], index=index)
    node = [n for n in model.nodes if n.label == "abstract.HasLicense"][0]
    assert "check" in node.stereotypes


def test_requires_is_drawn_from_the_level_that_imposed_it(abstract):
    """`Vlt` is subject to Backend's contract but did not impose it.

    Drawing the accumulated set here would attribute the obligation to the
    wrong level -- which is exactly what the diagram is for showing.
    """
    result, index = abstract
    model = inherit.build(result.pkg.task_m["abstract.Vlt"], index=index)
    assert [e for e in model.edges if e.kind == "requires"] == []


# ----------------------------------------------------------- descendants

def test_descendants_are_opt_in(abstract):
    """A widely-used base has too many to draw."""
    result, index = abstract
    model = inherit.build(result.pkg.task_m["abstract.Backend"], index=index)
    assert "abstract.Vlt" not in [n.label for n in model.nodes]


def test_descendants_are_drawn_when_asked_for(abstract):
    result, index = abstract
    model = inherit.build(result.pkg.task_m["abstract.Backend"], index=index,
                          descendants=True)
    labels = [n.label for n in model.nodes]
    assert "abstract.Vlt" in labels and "abstract.Vcs" in labels


def test_descendants_are_bounded_and_the_bound_is_recorded(abstract):
    result, index = abstract
    model = inherit.build(result.pkg.task_m["abstract.Backend"], index=index,
                          descendants=True, max_descendants=1)
    assert model.truncated is not None
    assert model.truncated.omitted == 1


# ------------------------------------------------------ a single box is not
# ------------------------------------------------------ a diagram

def test_a_task_with_no_relationships_produces_nothing(abstract):
    """One box repeats the heading and tells the reader nothing."""
    result, index = abstract
    model = inherit.build(result.pkg.task_m["abstract.Standalone"], index=index)
    assert model.is_empty()


# ---------------------------------------------------------------- types

def test_the_same_diagram_serves_types(types):
    """Same renderer, different accessor: a type's compartment is its fields."""
    result, index = types
    model = inherit.build_for_type(result.pkg.type_m["types.ObjFile"], index)
    assert [n.label for n in model.nodes] == ["types.ObjFile", "types.Artifact"]
    assert _attrs(model, "types.ObjFile") == ["arch"]
    assert _attrs(model, "types.Artifact") == ["origin"]


def test_subtypes_are_drawn_for_a_base_type(types):
    result, index = types
    model = inherit.build_for_type(result.pkg.type_m["types.Artifact"], index)
    labels = [n.label for n in model.nodes]
    assert "types.ObjFile" in labels and "types.Image" in labels


def test_an_unrelated_type_produces_nothing(types):
    result, index = types
    model = inherit.build_for_type(result.pkg.type_m["types.Unused"], index)
    assert model.is_empty()


def test_every_node_carries_a_link_target(chain):
    """Without `ref` the diagram loses the navigation that is most of its
    value -- and a class node's label IS its object name, so this is cheap."""
    model = inherit.build(chain.pkg.task_m["inherit.Leaf"])
    for node in model.nodes:
        assert node.ref == node.label

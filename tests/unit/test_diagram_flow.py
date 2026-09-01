"""The declared sub-flow diagram (design §6.2).

Almost every assertion here is about the difference between what the flow file
says and what a picture could be made to imply. A diagram is a claim, and the
easy failures are all claims nobody wrote down: an order between independent
tasks, an inference drawn as a declaration, a truncated view that reads as
complete.
"""

import os

import pytest

from dv_flow.doc.diagram import flow
from dv_flow.doc.diagram.model import node_id
from dv_flow.doc.loader import load_project


@pytest.fixture(scope="module")
def compound(request):
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "compound")
    result = load_project(root)
    assert result.ok
    return result


@pytest.fixture(scope="module")
def matrix(request):
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "matrix")
    result = load_project(root)
    assert result.ok
    return result


def _labels(model):
    return [n.label for n in model.nodes]


def _edges(model, kind=None):
    return [(e.src, e.dst) for e in model.edges
            if kind is None or e.kind == kind]


# -------------------------------------------------------------- basic shape

def test_subtasks_become_nodes(compound):
    model = flow.build(compound.pkg.task_m["compound.Build"])
    assert _labels(model) == ["gen-a", "gen-b", "link"]


def test_needs_become_edges(compound):
    model = flow.build(compound.pkg.task_m["compound.Build"])
    assert len(_edges(model, 'needs')) == 2


def test_independent_subtasks_get_no_edge_between_them(compound):
    """`gen-a` and `gen-b` declare nothing about each other.

    Inventing an order from file order would be a fork drawn as a sequence --
    a claim the flow file does not make, and the one a reader is most likely to
    act on.
    """
    model = flow.build(compound.pkg.task_m["compound.Build"])
    ids = {n.label: n.id for n in model.nodes}
    pairs = set(_edges(model))
    assert (ids["gen-a"], ids["gen-b"]) not in pairs
    assert (ids["gen-b"], ids["gen-a"]) not in pairs


def test_a_task_with_no_body_produces_an_empty_model(compound):
    """An empty diagram is not rendered at all.

    An empty box reads as "this task has no structure", when the truth is
    "this view does not apply here".
    """
    leaf = [s for s in compound.pkg.task_m["compound.Build"].subtasks
            if s.leafname == "gen-a"][0]
    assert flow.build(leaf).is_empty()


# ------------------------------------------------------------------ depth

def test_a_nested_compound_is_one_box_by_default(compound):
    """A compound's own body is its interface; its subtasks' bodies are theirs.

    Inlining them would produce a wall rather than a diagram, and would repeat
    on the nested task's own page.
    """
    model = flow.build(compound.pkg.task_m["compound.Nested"])
    shapes = {n.label: n.shape for n in model.nodes}
    assert shapes["inner"] == "call"
    assert shapes["prep"] == "action"


def test_a_body_reached_through_uses_still_counts_as_compound(compound):
    """`inner` writes `uses: compound.Build` and has no subtasks of its own.

    Reading only the subtask's own list would draw it as a leaf, understating
    the flow exactly where the reader most needs to know there is more inside.
    """
    inner = [s for s in compound.pkg.task_m["compound.Nested"].subtasks
             if s.leafname == "inner"][0]
    assert not getattr(inner, 'subtasks', None)
    assert flow._has_body(inner)


def test_a_call_node_links_to_the_task_it_uses(compound):
    """Labelled `inner`, but the page a reader wants is `compound.Build`'s."""
    model = flow.build(compound.pkg.task_m["compound.Nested"])
    inner = [n for n in model.nodes if n.label == "inner"][0]
    assert inner.ref == "compound.Build"


# ------------------------------------------------------------------ guards

def test_iff_is_a_guard_on_the_node_not_a_decision_node(compound):
    """A guard is a condition on reaching a step.

    Rendering it as a separate diamond would imply a branch point the flow file
    never declared -- and would suggest an alternative path that does not exist.
    """
    model = flow.build(compound.pkg.task_m["compound.Guarded"])
    guards = {n.label: n.guard for n in model.nodes}
    assert guards["sometimes"] == "${{ false }}"
    assert guards["always"] == ""
    assert len(model.nodes) == 2


# ---------------------------------------------------------------- dataflow

def test_dataflow_edges_are_inferred_and_marked(compound):
    """A `needs:` edge says "after"; it does not say "consumes what it made".

    Recovering the object flow is useful and is still an inference: two tasks
    can match without the author ever intending a data dependency. Drawing it
    like a declaration would be a lie.
    """
    model = flow.build(compound.pkg.task_m["compound.Dataflow"])
    inferred = [e for e in model.edges if e.inferred]
    assert len(inferred) == 1
    assert inferred[0].kind == 'dataflow'
    assert inferred[0].label == 'compound.Obj'


def test_declared_edges_are_never_marked_inferred(compound):
    model = flow.build(compound.pkg.task_m["compound.Dataflow"])
    for edge in model.edges:
        if edge.kind == 'needs':
            assert edge.inferred is False


def test_dataflow_can_be_turned_off(compound):
    """A reader who wants only what the author declared should get exactly
    that."""
    model = flow.build(compound.pkg.task_m["compound.Dataflow"],
                       dataflow=False)
    assert [e for e in model.edges if e.inferred] == []
    assert _edges(model, 'needs')


def test_no_dataflow_edge_without_matching_patterns(compound):
    """`Build`'s subtasks declare no produces/consumes at all."""
    model = flow.build(compound.pkg.task_m["compound.Build"])
    assert [e for e in model.edges if e.kind == 'dataflow'] == []


# ----------------------------------------------------------------- regions

def test_a_matrix_body_is_drawn_once(matrix):
    """The design's main diagram claim.

    A 3x2 matrix elaborated is six near-identical boxes that teach a reader
    nothing about the structure they need to modify. One node in one labelled
    region is smaller, truer to what the author wrote, and reproducible.
    """
    model = flow.build(matrix.pkg.task_m["matrix.Sweep"])
    assert len(model.nodes) == 1
    assert len(model.regions) == 1


def test_the_region_names_its_axes(matrix):
    """The axis structure is the whole point of drawing a region, so each
    axis's values are bracketed rather than run together."""
    region = flow.build(matrix.pkg.task_m["matrix.Sweep"]).regions[0]
    assert region.kind == 'expansion'
    assert region.label == "for each {sim: [vlt, vcs, xcelium], opt: [-O0, -O2]}"


def test_the_region_contains_the_whole_body(matrix):
    """A `matrix:` parameterizes the body, not one task in it."""
    model = flow.build(matrix.pkg.task_m["matrix.Sweep"])
    assert model.regions[0].nodes == model.node_ids()


def test_no_region_without_a_strategy(matrix):
    model = flow.build(matrix.pkg.task_m["matrix.Plain"])
    assert model.regions == []


def test_the_model_is_never_elaborated(matrix):
    """M3 produces declared views only. An elaborated diagram is one machine's
    expansion of one configuration and has to be labelled as such."""
    assert flow.build(matrix.pkg.task_m["matrix.Sweep"]).elaborated is False


# --------------------------------------------------------------- truncation

def test_the_node_cap_records_what_it_dropped(compound):
    """Silent truncation is the worst outcome: a capped diagram that reads as
    complete tells the reader something false with no way to notice."""
    model = flow.build(compound.pkg.task_m["compound.Build"], max_nodes=2)
    assert len(model.nodes) == 2
    assert model.truncated is not None
    assert model.truncated.omitted == 1
    assert "2" in model.truncated.reason


def test_no_truncation_record_when_nothing_was_dropped(compound):
    model = flow.build(compound.pkg.task_m["compound.Build"])
    assert model.truncated is None


# ---------------------------------------------------------------- ids

def test_node_ids_are_derived_from_names(compound):
    """Stable across edits: an id derived from position would make every
    golden churn when a sibling is added."""
    model = flow.build(compound.pkg.task_m["compound.Build"])
    assert model.nodes[0].id == node_id("compound.Build.gen-a")


def test_node_ids_are_diagram_safe(compound):
    model = flow.build(compound.pkg.task_m["compound.Build"])
    for node in model.nodes:
        assert all(c.isalnum() or c == '_' for c in node.id)
        assert not node.id[:1].isdigit()


def test_the_model_is_serializable(compound):
    import json
    model = flow.build(compound.pkg.task_m["compound.Dataflow"])
    json.dumps(model.to_dict())

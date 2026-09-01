"""The dataflow map and the package component view (§6.5, §6.6)."""

import os

import pytest

from dv_flow.doc.diagram import dataflow, package as package_diagram
from dv_flow.doc.indices import build_index
from dv_flow.doc.loader import load_project
from dv_flow.doc.package import documented_tasks, extract_package


@pytest.fixture(scope="module")
def types():
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "types")
    result = load_project(root)
    assert result.ok
    return result, build_index(result.pkg)


def _labels(model):
    return [n.label for n in model.nodes]


# ------------------------------------------------------------- dataflow map

def test_the_type_is_a_node_not_an_edge_label(types):
    """Routing through the type says what is true -- these produce it, those
    accept it -- with N+M edges instead of N×M.

    Drawing producer→consumer directly would suggest every producer feeds every
    consumer, which for two producers and two consumers is four claims where
    the flow file makes none.
    """
    result, index = types
    model = dataflow.build_for_type('types.ObjFile', index)
    assert 'types.ObjFile' in _labels(model)
    assert len(model.edges) == 4  # 2 producers + 2 consumers, not 2*2


def test_producers_point_at_the_type(types):
    result, index = types
    model = dataflow.build_for_type('types.ObjFile', index)
    from dv_flow.doc.diagram.model import node_id
    into = [e for e in model.edges if e.dst == node_id('types.ObjFile')]
    assert len(into) == 2


def test_a_qualifier_labels_only_the_consumer_that_asked_for_it(types):
    """`Link` takes any ObjFile; `Package` wants `arch=arm`.

    Labelling both edges with the qualifier would state a constraint `Link`
    never declared -- and would send a reader looking for an arm ObjFile they
    do not need.
    """
    result, index = types
    model = dataflow.build_for_type('types.ObjFile', index)
    from dv_flow.doc.diagram.model import node_id
    labels = {e.dst: e.label for e in model.edges
              if e.src == node_id('types.ObjFile')}
    assert labels[node_id('types.Package')] == 'arch=arm'
    assert labels[node_id('types.Link')] == ''


def test_an_untouched_type_produces_nothing(types):
    result, index = types
    assert dataflow.build_for_type('types.Unused', index).is_empty()


def test_the_package_map_covers_every_type(types):
    result, index = types
    model = dataflow.build_for_package(result.pkg, index)
    for name in ('types.ObjFile', 'types.Image', 'types.Report'):
        assert name in _labels(model)


def test_the_package_map_excludes_undocumented_tasks(types):
    """A map routing through an internal task tells the reader to use
    something they cannot name."""
    result, index = types
    model = dataflow.build_for_package(
        result.pkg, index, documented=[])
    assert model.is_empty()


def test_the_package_map_records_truncation(types):
    result, index = types
    model = dataflow.build_for_package(
        result.pkg, index,
        documented=documented_tasks(result.pkg), max_nodes=3)
    assert model.truncated is not None
    assert model.truncated.omitted > 0


def test_truncation_drops_dangling_edges(types):
    """An edge to a node that was cut would render as an arrow into nothing."""
    result, index = types
    model = dataflow.build_for_package(
        result.pkg, index,
        documented=documented_tasks(result.pkg), max_nodes=3)
    ids = {n.id for n in model.nodes}
    for edge in model.edges:
        assert edge.src in ids and edge.dst in ids


# --------------------------------------------------------- component view

def test_provided_interfaces_are_the_types_produced(types):
    result, index = types
    doc = extract_package(result.pkg)
    model = package_diagram.build(result.pkg, index, doc=doc)
    provided = [e for e in model.edges if e.label == 'provides']
    assert len(provided) == 3


def test_a_type_produced_here_is_not_also_required(types):
    """Consumed AND produced here is internal plumbing.

    A reader deciding whether they can use this package does not have to supply
    `ObjFile` -- the package makes its own.
    """
    result, index = types
    doc = extract_package(result.pkg)
    model = package_diagram.build(result.pkg, index, doc=doc)
    required = [e for e in model.edges if e.label == 'requires']
    assert required == []


def test_imports_are_drawn(types):
    result, index = types
    doc = extract_package(result.pkg)
    model = package_diagram.build(result.pkg, index, doc=doc)
    imports = [e for e in model.edges if e.kind == 'import']
    assert len(imports) == 1
    assert 'std' in _labels(model)


def test_a_required_interface_appears_when_nothing_produces_it(data_dir):
    """`library` consumes `std.FileSet` and produces none, so it needs one
    from outside -- which is exactly what a prospective user must know."""
    result = load_project(os.path.join(data_dir, "library"))
    index = build_index(result.pkg)
    doc = extract_package(result.pkg)
    model = package_diagram.build(result.pkg, index, doc=doc)
    required = [e for e in model.edges if e.label == 'requires']
    assert required, "expected a required interface"


def test_the_model_is_serializable(types):
    import json
    result, index = types
    json.dumps(dataflow.build_for_package(result.pkg, index).to_dict())
    json.dumps(package_diagram.build(
        result.pkg, index, doc=extract_package(result.pkg)).to_dict())

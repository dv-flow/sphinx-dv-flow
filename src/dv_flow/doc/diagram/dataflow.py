"""The dataflow map (design §6.5).

A bipartite **producer → type → consumer** graph, built from the reverse index.

The type sits in the middle as a node of its own rather than being a label on a
direct producer→consumer edge. That is deliberate: several tasks may produce the
same type and several consume it, and drawing the cross product would suggest
every producer feeds every consumer. Routing through the type says what is
actually true -- these produce it, those accept it -- with N+M edges instead of
N×M.

For a package this is the closest thing to "what can I plug into what" that a
flow library has, and it is the most likely centrepiece for a library package
with no runnable tasks at all.
"""

from typing import List, Optional

from .model import DiagramEdge, DiagramModel, DiagramNode, Truncated, node_id

DEFAULT_MAX_NODES = 60


def _type_node(name) -> DiagramNode:
    return DiagramNode(id=node_id(name), label=name, ref=name, shape='type')


def _task_node(name) -> DiagramNode:
    return DiagramNode(id=node_id(name), label=name, ref=name, shape='action')


def _qualifier(index, type_name, consumer) -> str:
    """What `consumer` asked for beyond the bare type, if anything.

    Per consumer, not per type. `std.FileSet` is one type carrying many
    different contents, so an unlabelled edge would suggest any producer feeds
    any consumer -- but labelling every edge into a type with the same
    qualifier is the opposite error, stating a constraint the other consumers
    never declared.
    """
    return index.consumed_as.get(type_name, {}).get(consumer, "")


def build_for_type(type_name, index, max_nodes=DEFAULT_MAX_NODES) -> DiagramModel:
    """The map centred on one type: who makes it, who takes it."""
    model = DiagramModel(kind='dataflow', title=type_name)

    producers = list(index.produced_by.get(type_name, []))
    consumers = list(index.consumed_by.get(type_name, []))
    if not producers and not consumers:
        return model

    model.add_node(_type_node(type_name))
    for name in producers:
        model.add_node(_task_node(name))
        model.edges.append(DiagramEdge(
            src=node_id(name), dst=node_id(type_name), kind='dataflow'))

    for name in consumers:
        model.add_node(_task_node(name))
        model.edges.append(DiagramEdge(
            src=node_id(type_name), dst=node_id(name), kind='dataflow',
            label=_qualifier(index, type_name, name)))

    return model


def build_for_package(pkg, index, documented=None,
                      max_nodes=DEFAULT_MAX_NODES) -> DiagramModel:
    """The map over a whole package.

    `documented` limits it to the tasks a reader can actually reach. A map that
    routes through an internal task tells them to use something they cannot
    name, which is worse than a smaller map.
    """
    model = DiagramModel(kind='dataflow', title=getattr(pkg, 'name', ''))

    allowed = None
    if documented is not None:
        allowed = {getattr(t, 'name', t) for t in documented}

    def _permitted(name):
        return allowed is None or name in allowed

    types = set()
    for type_name, names in index.produced_by.items():
        if any(_permitted(n) for n in names):
            types.add(type_name)
    for type_name, names in index.consumed_by.items():
        if any(_permitted(n) for n in names):
            types.add(type_name)

    if not types:
        return model

    seen = set()

    def _add(node):
        if node.id not in seen:
            seen.add(node.id)
            model.add_node(node)

    for type_name in sorted(types):
        _add(_type_node(type_name))
        for name in index.produced_by.get(type_name, []):
            if not _permitted(name):
                continue
            _add(_task_node(name))
            model.edges.append(DiagramEdge(
                src=node_id(name), dst=node_id(type_name), kind='dataflow'))
        for name in index.consumed_by.get(type_name, []):
            if not _permitted(name):
                continue
            _add(_task_node(name))
            model.edges.append(DiagramEdge(
                src=node_id(type_name), dst=node_id(name), kind='dataflow',
                label=_qualifier(index, type_name, name)))

    if len(model.nodes) > max_nodes:
        omitted = len(model.nodes) - max_nodes
        kept = {n.id for n in model.nodes[:max_nodes]}
        model.nodes = model.nodes[:max_nodes]
        model.edges = [e for e in model.edges
                       if e.src in kept and e.dst in kept]
        model.truncated = Truncated(
            reason="more than %d nodes in the package map" % max_nodes,
            omitted=omitted)

    return model

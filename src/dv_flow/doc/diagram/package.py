"""The package component view (design §6.6).

Packages have provided and required interfaces, so the UML component view fits
with no strain:

    provided   the item types this package's tasks produce
    required   the item types its tasks consume but do not produce
    imports    the packages it depends on

The *required* set is the useful half, and it is the one a package cannot state
about itself. A type consumed and also produced here is internal plumbing; a
type consumed and never produced is something the package needs from outside,
which is exactly what someone deciding whether they can use it wants to know.
"""

from typing import List, Optional

from .model import DiagramEdge, DiagramModel, DiagramNode, node_id


def build(pkg, index, doc=None, documented=None) -> DiagramModel:
    """The component view of `pkg`."""
    name = getattr(pkg, 'name', '')
    model = DiagramModel(kind='package', title=name)

    allowed = None
    if documented is not None:
        allowed = {getattr(t, 'name', t) for t in documented}

    def _permitted(task_name):
        return allowed is None or task_name in allowed

    produced = {t for t, names in index.produced_by.items()
                if any(_permitted(n) for n in names)}
    consumed = {t for t, names in index.consumed_by.items()
                if any(_permitted(n) for n in names)}

    # Consumed AND produced here is internal plumbing -- a reader deciding
    # whether they can use this package does not have to supply it.
    required = sorted(consumed - produced)
    provided = sorted(produced)

    imports = list(getattr(doc, 'imports', None) or [])

    if not (provided or required or imports):
        return model

    model.add_node(DiagramNode(
        id=node_id(name), label=name, ref=name, shape='call',
        stereotypes=['package']))

    for type_name in provided:
        model.add_node(DiagramNode(
            id=node_id(type_name), label=type_name, ref=type_name,
            shape='type'))
        model.edges.append(DiagramEdge(
            src=node_id(name), dst=node_id(type_name), kind='dataflow',
            label='provides'))

    for type_name in required:
        model.add_node(DiagramNode(
            id=node_id(type_name), label=type_name, ref=type_name,
            shape='type'))
        model.edges.append(DiagramEdge(
            src=node_id(type_name), dst=node_id(name), kind='dataflow',
            label='requires'))

    for import_name in imports:
        model.add_node(DiagramNode(
            id=node_id(import_name), label=import_name, ref=import_name,
            shape='call', stereotypes=['package']))
        model.edges.append(DiagramEdge(
            src=node_id(name), dst=node_id(import_name), kind='import',
            label='imports'))

    return model

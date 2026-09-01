"""The inheritance diagram -- a UML class view (design §6.4).

Verification libraries get deep (`std.Task` -> `hdl.sim.SimImage` ->
`hdl.sim.vlt.image` -> a project's own task), and no parameter table conveys
where a knob was introduced.

The attribute compartment lists the parameters **that level introduces**, not
the merged set. That is the same provenance the parameter table carries, made
spatial: a reader sees at a glance that `top` came from the simulator base and
`trace` from the project task. A box repeating every inherited parameter would
show the same list four times and say nothing.
"""

from typing import List, Optional

from .model import (DiagramEdge, DiagramModel, DiagramNode, Truncated,
                    node_id)

# A widely-used base has too many descendants to draw. Ancestors are always
# drawn -- there are never many, and they are the reason the diagram exists.
DEFAULT_MAX_DESCENDANTS = 12


def _own_params(task) -> List[str]:
    """Parameters introduced at this level, with override markers.

    A level that only *changes a default* shows the parameter with `= value`
    rather than as a fresh declaration -- which is the visual form of "this
    task changed one thing", the same statement the parameter table's
    provenance column makes in words.
    """
    param_defs = getattr(task, 'param_defs', None)
    definitions = getattr(param_defs, 'definitions', None) or {}
    if not definitions:
        return []

    inherited = _inherited_names(task)

    out = []
    for name in sorted(definitions):
        pdef = definitions[name]
        if name in inherited:
            value = getattr(pdef, 'value', None)
            if value not in (None, "", [], {}):
                out.append("%s = %s" % (name, value))
            else:
                # An override whose new value is empty -- `cli: false`, say --
                # is still an override. Rendering it bare would read as a fresh
                # declaration at this level, which is the one thing the
                # attribute compartment exists to get right.
                out.append("%s (override)" % name)
        else:
            out.append(name)
    return out


def _inherited_names(task):
    """Parameter names declared anywhere above this level."""
    from dv_flow.mgr.task import iter_uses_chain

    names = set()
    for level in iter_uses_chain(task):
        if level is task:
            continue
        param_defs = getattr(level, 'param_defs', None)
        names.update(getattr(param_defs, 'definitions', None) or {})
    return names


def _stereotypes(obj) -> List[str]:
    from ..lifecycle import read
    from ..task import _tag_docs

    out = []
    lifecycle = read(_tag_docs(getattr(obj, 'tags', None)))
    if lifecycle.declared and lifecycle.status != 'stable':
        out.append(lifecycle.status)
    if getattr(obj, 'check', None):
        out.append('check')
    return out


def _node_for(obj, own_params) -> DiagramNode:
    return DiagramNode(
        id=node_id(obj.name),
        label=obj.name,
        ref=obj.name,
        shape='class',
        tooltip=getattr(obj, 'desc', '') or (getattr(obj, 'doc', '') or '')[:80],
        stereotypes=_stereotypes(obj),
        # Italic in UML, and matching the abstract banner on the task's page.
        abstract=bool(getattr(obj, 'abstract', False)),
        attributes=own_params)


def build(task, index=None, descendants: bool = False,
          max_descendants: int = DEFAULT_MAX_DESCENDANTS) -> DiagramModel:
    """The class view for `task`, ancestors always, descendants on request."""
    from dv_flow.mgr.task import iter_uses_chain

    model = DiagramModel(kind='inherit', title=getattr(task, 'name', ''))

    chain = list(iter_uses_chain(task))
    if len(chain) == 1 and not (descendants and index is not None):
        # A task with no base and no drawn descendants is a single box. One box
        # is not a diagram -- it tells a reader nothing they did not get from
        # the heading.
        if not _own_params(task):
            return model

    seen = set()
    for level in chain:
        if level.name in seen:
            continue
        seen.add(level.name)
        model.add_node(_node_for(level, _own_params(level)))

    for derived, base in zip(chain, chain[1:]):
        model.edges.append(DiagramEdge(
            src=node_id(derived.name), dst=node_id(base.name), kind='uses'))

    # `requires:` is interface realization -- what the task obliges anything
    # deriving from it to satisfy. Drawn from the task's own declaration rather
    # than the accumulated set, so the diagram shows which LEVEL imposed it.
    for req in getattr(task, 'requires', None) or []:
        req_name = getattr(req, 'name', None)
        if not req_name:
            continue
        if req_name not in seen:
            seen.add(req_name)
            model.add_node(DiagramNode(
                id=node_id(req_name), label=req_name, ref=req_name,
                shape='class', stereotypes=['check']))
        model.edges.append(DiagramEdge(
            src=node_id(task.name), dst=node_id(req_name), kind='requires'))

    if descendants and index is not None:
        _add_descendants(model, task, index, max_descendants, seen)

    return model


def _add_descendants(model, task, index, max_descendants, seen):
    children = list(index.implementations.get(task.name, []))
    omitted = 0
    if len(children) > max_descendants:
        omitted = len(children) - max_descendants
        children = children[:max_descendants]
        model.truncated = Truncated(
            reason="more than %d descendants" % max_descendants,
            omitted=omitted)

    for name in children:
        if name not in seen:
            seen.add(name)
            model.add_node(DiagramNode(id=node_id(name), label=name,
                                       ref=name, shape='class'))
        model.edges.append(DiagramEdge(
            src=node_id(name), dst=node_id(task.name), kind='uses'))


def build_for_type(tt, index=None) -> DiagramModel:
    """The same diagram for a data type.

    Same renderer, different accessor: a type's attribute compartment is its
    fields rather than a task's parameters (design §6.4).
    """
    model = DiagramModel(kind='inherit', title=getattr(tt, 'name', ''))

    chain = []
    seen_ids = set()
    current = tt
    while current is not None and id(current) not in seen_ids:
        seen_ids.add(id(current))
        chain.append(current)
        current = getattr(current, 'uses', None)

    if len(chain) == 1 and not (index and index.derived_types.get(tt.name)):
        return model

    for level in chain:
        model.add_node(_node_for(level, _own_fields(level)))

    for derived, base in zip(chain, chain[1:]):
        model.edges.append(DiagramEdge(
            src=node_id(derived.name), dst=node_id(base.name), kind='uses'))

    if index is not None:
        for name in index.derived_types.get(tt.name, []):
            model.add_node(DiagramNode(id=node_id(name), label=name,
                                       ref=name, shape='class'))
            model.edges.append(DiagramEdge(
                src=node_id(name), dst=node_id(tt.name), kind='uses'))

    return model


def _own_fields(tt) -> List[str]:
    param_defs = getattr(tt, 'param_defs', None)
    return sorted(getattr(param_defs, 'definitions', None) or {})

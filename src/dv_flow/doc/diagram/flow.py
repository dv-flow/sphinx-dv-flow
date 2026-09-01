"""The declared sub-flow diagram (design §6.2).

Built from `Task.subtasks` and `Task.needs` -- the declaration, not an
elaboration. That is the design's main diagram claim, and it is worth restating
because the alternative is tempting: an elaborated graph is easy to get from
`TaskGraphBuilder` and looks impressive. It is also, for a 3x4x2 matrix, 24
near-identical boxes that teach a reader nothing about the structure they need
to modify -- and it is not reproducible, because it depends on the machine and
configuration that expanded it.

The declared view draws a parameterized body once, in a region labelled by its
axes. Smaller, truer to what the author wrote, and the same on every machine.
"""

from typing import Dict, List, Optional

from ..classify import classify
from .model import (DiagramEdge, DiagramModel, DiagramNode, DiagramRegion,
                    Truncated, node_id)

# Past this many nodes a diagram stops being readable. The cap produces a
# recorded truncation rather than an unreadable hairball -- and never a silent
# one, because a capped diagram that reads as complete is the worst outcome.
DEFAULT_MAX_NODES = 40

# A compound's own body is its interface; its subtasks' bodies are theirs. At
# depth 1 a nested compound is one box linking to its own page, which is also
# what makes the diagram a navigation surface rather than a wall.
DEFAULT_DEPTH = 1


def _stereotypes(task) -> List[str]:
    """UML stereotypes for a task box.

    Lifecycle first: someone reading a diagram to decide what to call should
    see «deprecated» before anything about how the task is implemented.
    """
    from ..lifecycle import read
    from ..task import _tag_docs

    out = []
    lifecycle = read(_tag_docs(getattr(task, 'tags', None)))
    if lifecycle.declared and lifecycle.status != 'stable':
        out.append(lifecycle.status)
    if getattr(task, 'shell', None) == 'pytask' and getattr(task, 'run', None):
        out.append('pytask')
    return out


def _has_body(task) -> bool:
    """Whether `task` is compound, including a body reached through `uses:`.

    A subtask written `uses: pkg.Build` has an empty `subtasks` of its own --
    the body is inherited, and the engine expands it at graph build. Reading
    only the task's own list would draw it as a leaf, which understates the
    flow at exactly the point a reader most needs to know there is more inside.
    """
    from dv_flow.mgr.task import iter_uses_chain

    for level in iter_uses_chain(task):
        if getattr(level, 'subtasks', None):
            return True
    return False


def _shape(task, depth_remaining: int) -> str:
    """`call` for a compound drawn as a single box, `action` for a leaf.

    The distinction is what tells a reader "there is more inside this one" --
    without it, a collapsed compound is indistinguishable from a leaf and the
    diagram quietly understates the flow.
    """
    if _has_body(task) and depth_remaining <= 0:
        return 'call'
    return 'action'


def _ref_for(task) -> str:
    """The documented object this node should link to.

    A subtask is usually not a documented object in its own right -- it lives
    inside its parent's body. What IS documented is the task it `uses:`, and
    that is the page a reader clicking it wants. Falls back to the subtask's own
    name, which simply will not resolve, leaving the node unlinked.
    """
    base = getattr(task, 'uses', None)
    base_name = getattr(base, 'name', None) if base is not None else None
    return base_name or getattr(task, 'name', '')


def _axes_text(axes) -> str:
    """`sim: [vlt, vcs], opt: [-O0, -O2]`.

    Each axis's values are bracketed. Without that the axes run together --
    "sim: vlt, vcs, opt: -O0" gives a reader no way to see where one ends, and
    the axis structure is the entire point of drawing a region.
    """
    return ", ".join(
        "%s: [%s]" % (name, ", ".join(str(v) for v in values))
        for name, values in (axes or {}).items())


def _matrix_region(task) -> Optional[DiagramRegion]:
    strategy = getattr(task, 'strategy', None)
    matrix = getattr(strategy, 'matrix', None) if strategy is not None else None
    if not matrix:
        return None
    return DiagramRegion(kind='expansion',
                         label="for each {%s}" % _axes_text(matrix))


def _select_region(task) -> Optional[DiagramRegion]:
    strategy = getattr(task, 'strategy', None)
    select = getattr(strategy, 'select', None) if strategy is not None else None
    if select is None:
        return None
    # "one of" and "for each" are different statements -- a choice is not a
    # fan-out -- so they get different region kinds and different wording.
    return DiagramRegion(
        kind='choice',
        label="one of {%s}" % _axes_text(getattr(select, 'axes', None)))


def _dataflow_edges(subtasks, ids) -> List[DiagramEdge]:
    """Object-flow edges, recovered by matching produces against consumes.

    A `needs:` edge says "after"; it does not say "consumes what it produced".
    Matching recovers the object flow, which is what an engineer tracing a
    verification flow actually wants. Every edge this returns is marked
    `inferred`, because an inference drawn as a declaration is a lie -- and
    these are genuinely inferences: two tasks can match without the author ever
    intending a data dependency.

    Uses the engine's own matcher rather than a second implementation, for the
    same reason as everything else: two answers to "does this satisfy that"
    would eventually disagree, and the graph is the half nobody checks.
    """
    try:
        from dv_flow.mgr.type_match import pattern_matches
    except ImportError:
        return []

    out = []
    for consumer in subtasks:
        consumes = getattr(consumer, 'consumes', None)
        if not isinstance(consumes, list) or not consumes:
            continue
        for producer in subtasks:
            if producer is consumer:
                continue
            produces = getattr(producer, 'produces', None) or []
            for wanted in consumes:
                if not isinstance(wanted, dict):
                    continue
                for item in produces:
                    if not isinstance(item, dict):
                        continue
                    if pattern_matches(wanted, item):
                        # Labelled with the item type: `std.FileSet` carries
                        # many different contents, and an unlabelled edge would
                        # suggest any producer feeds any consumer.
                        out.append(DiagramEdge(
                            src=ids[producer.name],
                            dst=ids[consumer.name],
                            kind='dataflow',
                            label=str(item.get('type', '')),
                            inferred=True))
                        break
                else:
                    continue
                break
    return out


def build(task, depth: int = DEFAULT_DEPTH,
          max_nodes: int = DEFAULT_MAX_NODES,
          dataflow: bool = True) -> DiagramModel:
    """The activity view of `task`'s declared body."""
    model = DiagramModel(kind='flow', title=getattr(task, 'name', ''))

    subtasks = list(getattr(task, 'subtasks', None) or [])
    if not subtasks:
        return model

    omitted = 0
    if len(subtasks) > max_nodes:
        omitted = len(subtasks) - max_nodes
        subtasks = subtasks[:max_nodes]
        model.truncated = Truncated(
            reason="more than %d subtasks" % max_nodes, omitted=omitted)

    ids: Dict[str, str] = {}
    for sub in subtasks:
        ids[sub.name] = node_id(sub.name)

    for sub in subtasks:
        model.add_node(DiagramNode(
            id=ids[sub.name],
            label=sub.leafname,
            ref=_ref_for(sub),
            shape=_shape(sub, depth - 1),
            tooltip=getattr(sub, 'desc', '') or '',
            stereotypes=_stereotypes(sub),
            abstract=bool(getattr(sub, 'abstract', False)),
            # A guard is a condition on reaching the node, not a node of its
            # own. Rendering it as a separate decision box would imply a
            # branch point the flow file never declared.
            guard=getattr(sub, 'iff', None) or ''))

    for sub in subtasks:
        for need in getattr(sub, 'needs', None) or []:
            need_name = getattr(need, 'name', None)
            if need_name is None:
                inner = getattr(need, 'task', None)
                need_name = getattr(inner, 'name', None)
            if need_name in ids:
                model.edges.append(DiagramEdge(
                    src=ids[need_name], dst=ids[sub.name], kind='needs'))

    if dataflow:
        model.edges.extend(_dataflow_edges(subtasks, ids))

    # The whole body sits inside the region: a `matrix:` parameterizes the
    # entire body, not one task in it.
    region = _matrix_region(task) or _select_region(task)
    if region is not None:
        region.nodes = [ids[s.name] for s in subtasks]
        model.regions.append(region)

    return model

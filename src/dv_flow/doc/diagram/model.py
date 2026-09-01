"""The diagram model (design §7).

Nodes, edges, regions and a truncation record. Two fields on it are
load-bearing rather than bookkeeping, and both exist to stop a picture from
saying something the flow file does not:

``edge.inferred``
    A dataflow edge is *recovered* by matching a producer's ``produces``
    against a consumer's ``consumes``. It is a true and useful inference, and
    it is not a declaration. Drawing it the same as a ``needs:`` edge would
    present an inference as a statement of intent.

``truncated``
    A capped diagram must not read as a complete one. Silent truncation is
    worse than either an unreadable diagram or an explicit "12 nodes omitted",
    because the reader has no way to know they are missing something.
"""

import dataclasses as dc
from typing import Any, Dict, List, Optional


def _to_jsonable(value):
    if dc.is_dataclass(value) and not isinstance(value, type):
        return value.to_dict()
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


@dc.dataclass
class _Part:
    def to_dict(self) -> Dict[str, Any]:
        return {f.name: _to_jsonable(getattr(self, f.name))
                for f in dc.fields(self)}


@dc.dataclass
class DiagramNode(_Part):
    # Stable within one diagram, and derived from the object's name rather than
    # from position -- an id that shifts when a sibling is added would make
    # every golden churn on an unrelated edit.
    id: str = ""
    label: str = ""
    # The OBJECT this node links to, which is not always what it is labelled.
    # A subtask written `uses: pkg.Build` is labelled with its local name --
    # `inner` -- but the page a reader wants is `pkg.Build`'s. Matching a link
    # on the label would find nothing, and the diagram would silently lose the
    # navigation that is most of its value.
    ref: str = ""
    # 'action' (a leaf task), 'call' (a compound, drawn as one box linking to
    # its own page), 'initial', 'final', 'decision', 'class', 'type'.
    shape: str = "action"
    # Filled by the renderer, which is the only layer that knows how documents
    # map to pages. Absent means "not documented here", which is a fact worth
    # keeping distinct from "documented but unlinked".
    url: Optional[str] = None
    tooltip: str = ""
    # UML stereotypes: «deprecated», «pytask», ... Drawn on the box.
    stereotypes: List[str] = dc.field(default_factory=list)
    abstract: bool = False
    # Rendered on the box for a class-view node: the parameters introduced at
    # THIS level, not the merged set (design §6.4).
    attributes: List[str] = dc.field(default_factory=list)
    # A guard condition (`iff:`) is a property of reaching this node, so it
    # rides on the node and is rendered on the incoming edge.
    guard: str = ""


@dc.dataclass
class DiagramEdge(_Part):
    src: str = ""
    dst: str = ""
    # 'needs' (control flow), 'dataflow' (object flow), 'uses'
    # (generalization), 'requires' (realization), 'import'.
    kind: str = "needs"
    label: str = ""
    # True when this edge was recovered rather than declared. Never drawn the
    # same as a declared edge.
    inferred: bool = False


@dc.dataclass
class DiagramRegion(_Part):
    """A container drawn around nodes: an expansion, a choice, or a loop.

    The region is what makes the declared view worth having. A `matrix:` body
    is drawn ONCE inside a region labelled by its axes, rather than expanded
    into one box per combination -- which is both smaller and closer to what
    the author actually wrote.
    """
    kind: str = "expansion"   # 'expansion' | 'choice' | 'loop' | 'decision'
    label: str = ""
    nodes: List[str] = dc.field(default_factory=list)


@dc.dataclass
class Truncated(_Part):
    reason: str = ""
    omitted: int = 0


@dc.dataclass
class DiagramModel(_Part):
    kind: str = "flow"        # 'flow' | 'inherit' | 'dataflow' | 'lattice'
    # False for every diagram M3 produces. An elaborated diagram is one
    # machine's expansion of one configuration, so it has to be labelled as
    # such wherever it appears -- see design §6.1.
    elaborated: bool = False
    title: str = ""
    nodes: List[DiagramNode] = dc.field(default_factory=list)
    edges: List[DiagramEdge] = dc.field(default_factory=list)
    regions: List[DiagramRegion] = dc.field(default_factory=list)
    truncated: Optional[Truncated] = None

    def add_node(self, node) -> DiagramNode:
        self.nodes.append(node)
        return node

    def node_ids(self):
        return [n.id for n in self.nodes]

    def is_empty(self) -> bool:
        """Whether there is anything here worth drawing.

        Empty is obvious. The less obvious case is a **single node with no
        edges and no region**: one box, drawn alone, showing a name the heading
        already gave. It is not a diagram, and rendering it costs the reader
        attention while telling them nothing -- the same argument that keeps a
        lone class out of the inheritance view.

        A single node *inside a region* is different and is worth drawing: the
        region label ("for each {sim: [...]}"), not the box, is the content.
        """
        if not self.nodes:
            return True
        return len(self.nodes) == 1 and not self.edges and not self.regions


def node_id(name: str) -> str:
    """A diagram-safe id for an object name.

    Derived from the name so it is stable across edits, and sanitized because
    every renderer this feeds has its own opinion about which characters may
    appear in an identifier.
    """
    out = []
    for ch in name:
        out.append(ch if (ch.isalnum() or ch == '_') else '_')
    ident = "".join(out)
    # A leading digit is not a legal identifier in mermaid or dot.
    return ident if not ident[:1].isdigit() else "n_" + ident

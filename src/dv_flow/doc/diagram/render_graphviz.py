"""Rendering a `DiagramModel` as Graphviz dot.

A second backend, not a second model. Both renderers consume the same
`DiagramModel`, so switching backends can change how a diagram looks and cannot
change what it says -- which is the property that makes `test_backends.py` a
meaningful test rather than a duplicate.

Graphviz earns its place on large graphs, where its layout is markedly better
than Mermaid's, and where a package-wide dataflow map is most likely to need it.
It costs an external tool on the build machine, which is why it is not the
default.
"""

from typing import List

from .model import DiagramModel

_SHAPES = {
    'action': 'box',
    # A UML call-behavior action. Doubling the border is dot's nearest
    # equivalent to Mermaid's subroutine box, and carries the same meaning:
    # there is more inside this one.
    'call': 'box, peripheries=2',
    'type': 'ellipse',
    'decision': 'diamond',
    'class': 'record',
}


def _escape(text) -> str:
    return (str(text)
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n'))


def _node_label(node) -> str:
    parts = ["«%s»" % s for s in node.stereotypes]
    parts.append(node.label)
    label = " ".join(parts)
    if node.attributes:
        # dot's record syntax: the class name, then the attribute compartment.
        # `|` separates compartments, `\\l` left-aligns each line.
        rows = "\\l".join(_escape(a) for a in node.attributes)
        return "{%s|%s\\l}" % (_escape(label), rows)
    return _escape(label)


def _node_attrs(node) -> str:
    attrs = ['label="%s"' % _node_label(node)]

    shape = _SHAPES.get(node.shape, 'box')
    if ', ' in shape:
        base, extra = shape.split(', ', 1)
        attrs.append('shape=%s' % base)
        attrs.append(extra)
    else:
        attrs.append('shape=%s' % shape)

    if node.abstract:
        # UML draws abstract classes in italics.
        attrs.append('fontname="Helvetica-Oblique"')
    if node.url:
        # The whole point of the U3 upstream hook: an SVG with URL attributes
        # is a navigable diagram rather than a picture of one.
        attrs.append('URL="%s"' % _escape(node.url))
    if node.tooltip:
        attrs.append('tooltip="%s"' % _escape(node.tooltip))
    return ", ".join(attrs)


def _edge_attrs(edge, guard="") -> str:
    attrs = []

    label = edge.label
    if guard:
        label = "%s [%s]" % (label, guard) if label else "[%s]" % guard
    if label:
        attrs.append('label="%s"' % _escape(label))

    if edge.kind == 'dataflow':
        # Dashed, exactly as in the Mermaid backend. An inferred edge that
        # looked declared in one backend and not the other would be worse than
        # either choice alone.
        attrs.append('style=dashed')
    elif edge.kind == 'uses':
        # UML generalization: hollow triangle at the base end.
        attrs.append('arrowhead=empty')
    elif edge.kind == 'requires':
        attrs.append('arrowhead=empty')
        attrs.append('style=dashed')
    elif edge.kind == 'import':
        attrs.append('style=dotted')

    if edge.inferred and 'style=dashed' not in attrs:
        attrs.append('style=dashed')

    return ", ".join(attrs)


def render(model: DiagramModel) -> str:
    lines = ['digraph "%s" {' % _escape(model.title or 'diagram')]
    lines.append('  rankdir=TB;')
    lines.append('  node [fontname="Helvetica", fontsize=10];')
    lines.append('  edge [fontname="Helvetica", fontsize=9];')

    region_of = {}
    for i, region in enumerate(model.regions):
        for node_ref in region.nodes:
            region_of[node_ref] = i

    for node in model.nodes:
        if node.id not in region_of:
            lines.append('  %s [%s];' % (node.id, _node_attrs(node)))

    for i, region in enumerate(model.regions):
        # `cluster_` is not a naming convention -- dot only draws a box around
        # a subgraph whose name starts with it.
        lines.append('  subgraph cluster_%d {' % i)
        lines.append('    label="%s";' % _escape(region.label))
        lines.append('    style=dashed;')
        for node in model.nodes:
            if region_of.get(node.id) == i:
                lines.append('    %s [%s];' % (node.id, _node_attrs(node)))
        lines.append('  }')

    guards = {n.id: n.guard for n in model.nodes}
    for edge in model.edges:
        attrs = _edge_attrs(edge, guards.get(edge.dst, ""))
        if edge.kind in ('uses', 'requires'):
            # `A -> B [arrowhead=empty]` with B the base, matching the
            # Mermaid backend's `B <|-- A`.
            head, tail = edge.dst, edge.src
            lines.append('  %s -> %s [%s];' % (tail, head, attrs))
        else:
            lines.append('  %s -> %s%s;' % (
                edge.src, edge.dst, (' [%s]' % attrs) if attrs else ''))

    lines.append('}')
    return "\n".join(lines)

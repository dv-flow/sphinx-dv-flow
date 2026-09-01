"""Rendering a `DiagramModel` as Mermaid.

Mermaid is the default backend because it needs no external tool: a docs build
that requires Graphviz on the machine is a docs build that some readers cannot
run, and the diagrams are supposed to make the documentation easier to keep,
not harder.

What this file is careful about is the same thing the model is careful about:
an inferred edge must not look like a declared one, and a truncated diagram must
not look complete.
"""

from typing import List

from .model import DiagramModel

# Mermaid arrow syntax per edge kind. The dashed forms are not decoration:
# `-.->` marks an edge that was recovered rather than declared, and a reader
# who cannot tell the two apart has been told something the flow file does not
# say.
_FLOW_ARROWS = {
    'needs': '-->',
    'dataflow': '-.->',
}

_CLASS_ARROWS = {
    # UML generalization: hollow triangle pointing at the base.
    'uses': '<|--',
    # UML realization: dashed, hollow triangle.
    'requires': '<|..',
}


def _escape(text) -> str:
    """Mermaid label text.

    Quotes delimit labels, and `${{ }}` -- which appears in guards and in
    output documentation -- contains braces that Mermaid would otherwise try to
    read as syntax.
    """
    return (str(text)
            .replace('"', "'")
            .replace('{', '&#123;')
            .replace('}', '&#125;')
            .replace('\n', ' '))


def _node_label(node) -> str:
    parts = []
    for stereotype in node.stereotypes:
        parts.append("«%s»" % stereotype)
    parts.append(node.label)
    return _escape(" ".join(parts))


def _node_line(node) -> str:
    label = _node_label(node)
    if node.shape == 'call':
        # A subroutine box: two extra bars, the UML call-behavior affordance.
        # It says "there is more inside this one", which is exactly what a
        # collapsed compound needs to say.
        return '    %s[["%s"]]' % (node.id, label)
    if node.shape == 'decision':
        return '    %s{"%s"}' % (node.id, label)
    if node.shape in ('initial', 'final'):
        return '    %s(("%s"))' % (node.id, label)
    return '    %s("%s")' % (node.id, label)


def render_flow(model: DiagramModel) -> str:
    lines = ["flowchart TD"]

    region_of = {}
    for i, region in enumerate(model.regions):
        for node in region.nodes:
            region_of[node] = i

    # Nodes outside any region first, then one subgraph per region. Mermaid
    # assigns a node to whichever subgraph declares it, so a node must not be
    # emitted twice.
    for node in model.nodes:
        if node.id not in region_of:
            lines.append(_node_line(node))

    for i, region in enumerate(model.regions):
        lines.append('    subgraph region_%d ["%s"]' % (i, _escape(region.label)))
        for node in model.nodes:
            if region_of.get(node.id) == i:
                lines.append('    ' + _node_line(node).lstrip())
        lines.append('    end')

    for edge in model.edges:
        arrow = _FLOW_ARROWS.get(edge.kind, '-->')
        label = edge.label
        # A guard belongs on the edge that reaches the node, not on the node:
        # `iff:` says when this step is taken, which is a property of getting
        # there.
        guard = _guard_for(model, edge.dst)
        if guard:
            label = "%s [%s]" % (label, guard) if label else "[%s]" % guard
        if label:
            # `A -->|"text"| B` -- the whole arrow, then the label. Trimming
            # the arrow's last character produces `--` / `-.-`, which Mermaid
            # parses as an undirected link and silently drops the arrowhead.
            lines.append('    %s%s|"%s"| %s' % (
                edge.src + ' ', arrow, _escape(label), edge.dst))
        else:
            lines.append('    %s %s %s' % (edge.src, arrow, edge.dst))

    lines.extend(_click_lines(model))
    return "\n".join(lines)


def _guard_for(model, node_id_):
    for node in model.nodes:
        if node.id == node_id_:
            return node.guard
    return ""


def _click_lines(model) -> List[str]:
    """`click` directives for nodes that have a URL.

    This is the feature that turns a diagram from an illustration into the
    package's table of contents. A node without a URL simply gets no click
    line -- it stays visible and readable, which is the right degradation for
    an object this doc set does not document.
    """
    out = []
    for node in model.nodes:
        if node.url:
            if node.tooltip:
                out.append('    click %s "%s" "%s"' % (
                    node.id, node.url, _escape(node.tooltip)))
            else:
                out.append('    click %s "%s"' % (node.id, node.url))
    return out


def render_class(model: DiagramModel) -> str:
    lines = ["classDiagram"]

    for node in model.nodes:
        lines.append("    class %s[\"%s\"] {" % (node.id, _escape(node.label)))
        for stereotype in node.stereotypes:
            lines.append("        <<%s>>" % _escape(stereotype))
        for attribute in node.attributes:
            lines.append("        +%s" % _escape(attribute))
        lines.append("    }")
        if node.abstract:
            # UML draws an abstract class in italics; Mermaid spells that as a
            # stereotype annotation.
            lines.append("    <<abstract>> %s" % node.id)

    for edge in model.edges:
        arrow = _CLASS_ARROWS.get(edge.kind, '<--')
        # `A <|-- B` reads "B derives from A", so the base is written first.
        lines.append("    %s %s %s" % (edge.dst, arrow, edge.src))

    lines.extend(_click_lines(model))
    return "\n".join(lines)


def render(model: DiagramModel) -> str:
    if model.kind == 'inherit':
        return render_class(model)
    return render_flow(model)

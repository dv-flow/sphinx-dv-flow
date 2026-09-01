"""Turning a `DiagramModel` into a rendered diagram, plus its textual twin.

Two rules from the design govern everything here.

**Every diagram has a textual twin** (ground rule 5). No information exists only
in a picture: a diagram that cannot be read -- by a screen reader, in a terminal,
in a diff -- must not be the only place a fact appears. So each diagram is
emitted alongside a table carrying the same edges.

**URLs come from the domain**, not from a second guess at where a task's page
went. A node for an object this doc set does not document simply gets no link;
it stays visible, which is the right degradation. Fabricating a URL would
produce a diagram that looks navigable and isn't.
"""

from docutils import nodes

from dv_flow.doc.diagram.render_graphviz import render as render_dot
from dv_flow.doc.diagram.render_mermaid import render as render_mermaid
from . import tables


class dvf_diagram(nodes.General, nodes.Element):
    """A diagram whose links are not resolvable yet.

    Directives run while documents are being READ, so the domain inventory is
    still filling: a task documented on a page not yet read is simply not there.
    Baking URLs in at directive time would silently drop every forward link --
    and worse, would do so depending on document order, so the same project
    would produce different diagrams under `-j` than under a serial build.

    The model is carried on this placeholder and rendered at `doctree-resolved`,
    when the inventory is complete. That is the same point Sphinx resolves its
    own cross-references, for the same reason.
    """


def resolve_urls(model, env, fromdocname, builder):
    """Fill in `node.url` for objects the `dvf` domain knows about.

    Goes through the domain's own inventory rather than reconstructing anchors,
    so a diagram link and a `:dvf:task:` reference cannot disagree about where
    a task's page is. An object that is not in the inventory -- undocumented,
    or `local` and therefore never documentable -- gets nothing, deliberately.
    """
    domain = env.get_domain('dvf')

    for node in model.nodes:
        target = node.ref or node.label
        entry = None
        for objtype in ('task', 'type', 'package'):
            entry = domain.objects.get((objtype, target))
            if entry is not None:
                break
        if entry is None:
            continue
        docname, anchor = entry
        try:
            uri = builder.get_relative_uri(fromdocname, docname)
        except Exception:
            # A builder with no notion of relative URIs (text, man). The
            # diagram is still worth emitting without links.
            continue
        node.url = "%s#%s" % (uri, anchor)


def diagram_block(model, backend='mermaid'):
    """The diagram itself, as the chosen backend's node.

    Both backends consume the same `DiagramModel`, so the choice can change how
    a diagram looks and cannot change what it says. Mermaid is the default
    because it needs no tool on the build machine; Graphviz earns its place on
    large graphs, where its layout is markedly better.
    """
    if backend == 'graphviz':
        return _graphviz_block(model)

    text = render_mermaid(model)
    try:
        from sphinxcontrib.mermaid import mermaid as mermaid_node
    except ImportError:
        # `sphinxcontrib-mermaid` is not installed. The diagram source is still
        # worth emitting: it is readable as text and complete, which beats
        # omitting the diagram entirely.
        node = nodes.literal_block(text, text)
        node['language'] = 'text'
        node['classes'] = ['dvf-diagram']
        return node
    out = mermaid_node()
    out['code'] = text
    out['options'] = {}
    return out


def _graphviz_block(model):
    text = render_dot(model)
    try:
        from sphinx.ext.graphviz import graphviz
    except ImportError:
        node = nodes.literal_block(text, text)
        node['language'] = 'text'
        node['classes'] = ['dvf-diagram']
        return node
    out = graphviz()
    out['code'] = text
    out['options'] = {'docname': ''}
    return out


def _edge_rows(model):
    rows = []
    labels = {n.id: n.label for n in model.nodes}
    for edge in model.edges:
        kind = edge.kind
        if edge.inferred:
            # Marked in the table as well as in the picture. The table is the
            # accessible copy, and dropping the distinction there would leave
            # an inference reading as a declaration for exactly the readers who
            # cannot check it against the diagram.
            kind += " (inferred)"
        rows.append((labels.get(edge.src, edge.src),
                     labels.get(edge.dst, edge.dst),
                     kind, edge.label))
    return rows


def text_twin(model):
    """The table (and prose) carrying the same information as the diagram.

    Edges are the usual content, but not the only content. A parameterized body
    -- one node inside a `for each {...}` region -- has no edges at all, and its
    region label is the entire point of the diagram. Emitting nothing there
    would leave that fact existing only in a picture, which is precisely what
    ground rule 5 forbids.
    """
    out = []

    if model.regions:
        for region in model.regions:
            para = nodes.paragraph()
            para += nodes.emphasis(text="%s: " % (
                "Repeated" if region.kind == 'expansion' else "Chosen"))
            para += nodes.Text(region.label)
            members = [n.label for n in model.nodes if n.id in region.nodes]
            if members:
                para += nodes.Text(" — containing %s" % ", ".join(members))
            out.append(para)

    rows = _edge_rows(model)
    if rows:
        table = tables.build(
            ("From", "To", "Relationship", "Item"),
            [(src, dst, kind, label or "\u2014") for src, dst, kind, label in rows],
            classes=['dvf-diagram-twin'])

        caption = nodes.paragraph(classes=['dvf-block-title'])
        caption += nodes.emphasis(text="Diagram as a table")
        out.append(caption)
        out.append(table)
    elif not model.regions and len(model.nodes) > 1:
        # Several unconnected nodes: a fork with nothing joining it. The names
        # are the content, and they are otherwise only in the picture.
        para = nodes.paragraph()
        para += nodes.emphasis(text="Independent steps: ")
        para += nodes.Text(", ".join(n.label for n in model.nodes))
        out.append(para)

    if not out:
        return []

    container = nodes.container(classes=['dvf-diagram-twin-wrapper'])
    container += out
    return [container]


def truncation_note(model):
    """An explicit record that the diagram is incomplete.

    Silent truncation is the worst outcome: a capped diagram that reads as
    complete tells the reader something false and gives them no way to notice.
    """
    if model.truncated is None:
        return []
    note = nodes.warning()
    para = nodes.paragraph()
    para += nodes.Text(
        "This diagram is truncated: %s, %d not shown."
        % (model.truncated.reason, model.truncated.omitted))
    note += para
    return [note]


def render_model(model, twin=True, backend=None):
    """Diagram placeholder, truncation note, and textual twin.

    The twin and the note are built now -- neither depends on links -- while
    the diagram itself waits for `resolve_diagrams` below.
    """
    if model.is_empty():
        return []

    placeholder = dvf_diagram()
    placeholder['dvf_model'] = model
    placeholder['dvf_backend'] = backend

    out = [placeholder]
    out += truncation_note(model)
    if twin:
        out += text_twin(model)
    return out


def resolve_diagrams(app, doctree, fromdocname):
    """`doctree-resolved` handler: fill in links and render.

    By now every document has been read, so the domain knows about every
    documented object and a forward link resolves exactly like a backward one.
    """
    env = app.builder.env
    default_backend = env.config.dvflow_diagram_backend
    for placeholder in list(doctree.findall(dvf_diagram)):
        model = placeholder['dvf_model']
        resolve_urls(model, env, fromdocname, app.builder)
        backend = placeholder.get('dvf_backend') or default_backend
        placeholder.replace_self(diagram_block(model, backend))

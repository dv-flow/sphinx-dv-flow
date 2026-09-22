"""The shared content blocks (design §5).

One renderer per block, assembled per kind in `kinds.py`. Splitting it this way
is what stops a root page and a library page from growing two slightly different
parameter tables.
"""

import os

from docutils import nodes

from . import lifecycle as lifecycle_render
from . import schema
from .docfield import parse_doc

# Rendered when a task inherits the engine's `consumes` default. It reads as
# what it is -- an absence -- rather than as a contract the author wrote.
UNDECLARED_CONSUMES = "not declared — accepts all inputs"


def _admonition(title, body_nodes, classes):
    node = nodes.container(classes=classes)
    para = nodes.paragraph()
    para += nodes.strong(text=title)
    node += para
    node += body_nodes
    return node


def section_title(text, key=None, state=None):
    """A block heading, linked to its schema entry when the block is a key.

    "Parameters" is the `with:` key wearing a friendlier name, and the reader
    who wants to know what may go in one is the reader looking at the table.
    """
    para = nodes.paragraph(classes=['dvf-block-title'])
    label = schema.label(text, key, state) if key else text
    if isinstance(label, str):
        para += nodes.strong(text=label)
    else:
        strong = nodes.strong()
        strong += label
        para += strong
    return para


def badges(doc):
    """Scope and lifecycle badges for the header line.

    Read defensively: the header is shared by every documented object, and
    configurations have no visibility and carry no tags. A block that only
    works for tasks would be a second header renderer in everything but name.
    """
    out = ["[%s]" % scope for scope in (getattr(doc, 'scope', None) or [])]
    if getattr(doc, 'kind', None) == 'abstract':
        out.append("[abstract]")
    label = (lifecycle_render.badge_text(doc)
             if getattr(doc, 'tags', None) else None)
    if label:
        out.append("[%s]" % label)
    return out


def header(doc):
    """Name, badges and one-line description."""
    result = []

    para = nodes.paragraph(classes=['dvf-header'])
    for badge in badges(doc):
        para += nodes.inline(text=badge, classes=['dvf-badge'])
        para += nodes.Text(" ")
    if doc.desc:
        para += nodes.Text(doc.desc)
    if para.children:
        result.append(para)

    return result


def lifecycle(doc):
    """The lifecycle banner. See `render/lifecycle.py` for why it goes first."""
    return lifecycle_render.banner(doc)


def description(doc, state, srcfile=None):
    """The `doc:` field, parsed as reStructuredText."""
    if not doc.doc:
        return []
    line = doc.srcinfo.line if doc.srcinfo else 0
    return parse_doc(doc.doc, state,
                     source=srcfile or (doc.srcinfo.file if doc.srcinfo else None),
                     line=line)


def signature(doc):
    """The `uses:` chain, most-derived first.

    Rendered as a chain rather than only the immediate base: a reader asking
    "what is this built on" usually wants the whole line, and the intermediate
    task is often the one with the documentation.
    """
    if not doc.uses_chain:
        return []
    para = nodes.paragraph()
    para += nodes.strong(text="Uses: ")
    for i, name in enumerate(doc.uses_chain):
        if i:
            para += nodes.Text(" → ")
        para += nodes.literal(text=name)
    return [para]


def _field_list(rows):
    """`rows` is [(label, [nodes])]. Empty rows are skipped by the caller.

    A label may be a string or a list of nodes -- the latter is how a schema
    cross-link gets into a field name without every caller having to know
    whether one is configured.
    """
    field_list = nodes.field_list()
    for label, body in rows:
        field = nodes.field()
        if isinstance(label, str):
            field += nodes.field_name(text=label)
        else:
            name = nodes.field_name()
            name += label
            field += name
        field_body = nodes.field_body()
        field_body += body
        field += field_body
        field_list += field
    return field_list


def dataflow(doc, state=None):
    """`consumes` / `produces` / `passthrough` -- the type signature of a task.

    The distinguishing content of a library page. Three things this has to get
    right, all of them about not overstating a contract:

    - an undeclared `consumes` renders as an absence, visually distinct from a
      declaration, because the engine's default is not a claim the author made;
    - `produces` declares what MAY be produced, said once in the heading rather
      than hedged on every row;
    - an inherited declaration is still a declaration, so it renders normally.
    """
    rows = []

    consumes_body = nodes.paragraph()
    if not doc.consumes_declared:
        consumes_body += nodes.emphasis(text=UNDECLARED_CONSUMES)
    else:
        consumes = doc.consumes
        if isinstance(consumes, list):
            bullet = nodes.bullet_list()
            for entry in consumes:
                item = nodes.list_item()
                para = nodes.paragraph()
                para += nodes.literal(text=_pattern_text(entry))
                item += para
                bullet += item
            consumes_body = bullet
        else:
            text = str(consumes)
            if text.endswith("No"):
                consumes_body += nodes.Text("none — this task takes no inputs")
            else:
                consumes_body += nodes.Text(text.split('.')[-1].lower())
    rows.append((schema.label("Consumes", "consumes", state), consumes_body))

    if doc.produces:
        bullet = nodes.bullet_list()
        for entry in doc.produces:
            item = nodes.list_item()
            para = nodes.paragraph()
            para += _type_xref(entry.type)
            if entry.attrs:
                para += nodes.Text(" ")
                para += nodes.literal(text=_attrs_text(entry.attrs))
            if entry.doc:
                # The type says what KIND of thing this is; the prose says
                # which thing. Rendered as literal text because it is usually a
                # path, and shown verbatim because the unresolved
                # `${{ task_rundir }}` is the part that generalises -- a
                # resolved path would only be true on the machine that built
                # the docs.
                para += nodes.Text(" — ")
                para += nodes.literal(text=entry.doc)
            item += para
            bullet += item
        rows.append((schema.label("Produces (may produce)", "produces", state),
                     bullet))

    if rows:
        return [_field_list(rows)]
    return []


def _pattern_text(entry):
    if isinstance(entry, dict):
        return ", ".join("%s=%s" % (k, v) for k, v in entry.items())
    return str(entry)


def _attrs_text(attrs):
    return ", ".join("%s=%s" % (k, v) for k, v in attrs.items())


def _type_xref(name):
    """A produced/consumed item type, as a cross-reference when resolvable.

    A pending xref rather than plain literal text: the type is the vocabulary
    the dataflow speaks, and being able to click through to it is most of the
    value of documenting types at all. Unresolved references degrade to the
    literal text (M2 registers the targets).
    """
    from sphinx import addnodes

    ref = addnodes.pending_xref(
        '', refdomain='dvf', reftype='type', reftarget=name,
        refexplicit=False, refwarn=False)
    ref += nodes.literal(text=name)
    return ref


def needs(doc, state=None):
    if not doc.needs:
        return []
    bullet = nodes.bullet_list()
    for name in doc.needs:
        item = nodes.list_item()
        para = nodes.paragraph()
        para += _task_xref(name)
        item += para
        bullet += item
    return [_field_list([(schema.label("Needs", "needs", state), bullet)])]


def _task_xref(name):
    from sphinx import addnodes

    ref = addnodes.pending_xref(
        '', refdomain='dvf', reftype='task', reftarget=name,
        refexplicit=False, refwarn=False)
    ref += nodes.literal(text=name)
    return ref


def facts(doc, state=None):
    """The collapsed behavior table.

    Only what was actually set: a table of engine defaults tells the reader
    nothing and crowds out the one row that does.
    """
    if not doc.behavior:
        return []
    rows = []
    for key in sorted(doc.behavior):
        body = nodes.paragraph()
        body += nodes.literal(text=str(doc.behavior[key]))
        # The facts table is the one place the raw key names already appear, so
        # it is where a schema link is most obviously right.
        rows.append((schema.label(key, key, state), body))
    return [_field_list(rows)]


def examples(doc, state, srcfile=None):
    """Worked examples, each as a titled code block.

    A literal block, not a bullet list: example code is meant to be copied, and
    bullets are not part of what the reader should type.

    Three things beyond the code, all of them about what the reader may assume:
    an adjacent file is included rather than shown as a path; a generated
    snippet says it was synthesized rather than asserted; and a flow fragment
    the engine refused says so *next to the code*, where someone about to copy
    it will see it.
    """
    from . import examples as render_examples

    out = []
    for i, ex in enumerate(doc.examples):
        if ex.origin == 'file':
            out += render_examples.include_file(ex, state)
            continue

        title = ex.title or "Example %d" % (i + 1)
        para = nodes.paragraph()
        para += nodes.strong(text=title)
        if ex.origin == 'generated':
            para += nodes.Text(" ")
            para += nodes.emphasis(text="(generated)")
        out.append(para)
        if ex.caption:
            out.extend(parse_doc(ex.caption, state, source=srcfile))
        block = nodes.literal_block(ex.code, ex.code)
        block['language'] = ex.lang or 'text'
        out.append(block)
        out += render_examples.validity(ex)
        out += render_examples.diagram(ex)
    return out


def source(doc, base_dir=None):
    """A `file:line` pointer to the declaration.

    Relativized when possible: an absolute path from someone else's machine is
    noise, and the reader wants to know where in *their* checkout to look.
    """
    if doc.srcinfo is None or not doc.srcinfo.file:
        return []
    path = doc.srcinfo.file
    if base_dir:
        try:
            path = os.path.relpath(path, base_dir)
        except ValueError:
            pass
    # Line 0 means "somewhere in this file" -- it is what a declaration with no
    # recorded position yields. Printing `file:0` looks like a location and
    # sends a reader to the top of the file believing that is where to look.
    where = ("%s:%d" % (path, doc.srcinfo.line)) if doc.srcinfo.line else path
    para = nodes.paragraph(classes=['dvf-source'])
    # Always a reference, even when viewcode is off or the builder is not HTML:
    # rendering has no access to configuration, so the decision is made in
    # `viewcode.resolve_links`, which unwraps the node back to this same text.
    from ..viewcode import make_source_node
    para += make_source_node("Defined in %s" % where,
                             doc.srcinfo.file, doc.srcinfo.line)
    return [para]

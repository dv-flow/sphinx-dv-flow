"""Rendering a data type (design §4.6).

A type's own declaration is thin. Most of the page is the reverse direction --
who produces this, who consumes it, what derives from it -- which is what a
reader actually arrives with: "I have an ObjFile, what can take one?"
"""

from docutils import nodes

from . import tables
from .blocks import (_field_list, _task_xref, _type_xref, description,
                     source)
from .docfield import first_paragraph


def _name_list(names, xref):
    bullet = nodes.bullet_list()
    for name in names:
        item = nodes.list_item()
        para = nodes.paragraph()
        para += xref(name)
        item += para
        bullet += item
    return bullet


def _fields_table(doc):
    if not doc.params:
        return []

    rows = []
    for param in doc.params:
        default = (nodes.Text("—") if param.default in (None, "")
                   else nodes.literal(text=str(param.default)))
        desc = [nodes.Text(first_paragraph(param.doc) or param.desc or "")]
        if param.inherited and param.declared_by:
            desc.append(nodes.Text(" "))
            desc.append(nodes.emphasis(text="(from %s)" % param.declared_by))
        rows.append([
            nodes.literal(text=param.name),
            nodes.literal(text=param.type),
            default,
            desc,
        ])

    return [tables.build(("Field", "Type", "Default", "Description"), rows,
                         classes=['dvf-type-fields'])]


def render(doc, state, base_dir=None, show_source=True):
    out = []

    header = nodes.paragraph(classes=['dvf-header'])
    for facet in doc.facets:
        header += nodes.inline(text="[%s]" % facet, classes=['dvf-badge'])
        header += nodes.Text(" ")
    if doc.uses_chain:
        header += nodes.Text("Extends ")
        header += _type_xref(doc.uses_chain[0])
    if header.children:
        out.append(header)

    out += description(doc, state)

    if 'check' in doc.facets:
        # A check type is not a data item at all -- it is a contract evaluated
        # at graph build. A reader who assumes otherwise will try to produce
        # one, so say what it is before showing anything else about it.
        note = nodes.note()
        para = nodes.paragraph()
        para += nodes.Text(
            "This is a check type: tasks name it in ")
        para += nodes.literal(text="requires:")
        para += nodes.Text(" and it is evaluated at graph build. It is not an "
                           "item that flows through the graph.")
        if doc.check:
            para += nodes.Text(" Implemented by ")
            para += nodes.literal(text=doc.check)
            para += nodes.Text(".")
        note += para
        out.append(note)

    fields = _fields_table(doc)
    if fields:
        para = nodes.paragraph(classes=['dvf-block-title'])
        para += nodes.strong(text="Fields")
        out.append(para)
        out += fields

    rows = []
    if doc.produced_by:
        rows.append(("Produced by", _name_list(doc.produced_by, _task_xref)))
    if doc.consumed_by:
        rows.append(("Consumed by", _name_list(doc.consumed_by, _task_xref)))
    if doc.derived_by:
        rows.append(("Extended by", _name_list(doc.derived_by, _type_xref)))

    if rows:
        para = nodes.paragraph(classes=['dvf-block-title'])
        para += nodes.strong(text="Used by")
        out.append(para)
        out.append(_field_list(rows))
    elif 'check' not in doc.facets:
        # Silence here would read as "not yet documented". It is a fact about
        # the package -- a type nothing produces or consumes is either unused
        # or reached from outside it -- and worth stating rather than leaving
        # the reader to wonder whether the page is incomplete.
        para = nodes.paragraph()
        para += nodes.emphasis(text=(
            "No task in this package produces or consumes this type."))
        out.append(para)

    if show_source:
        out += source(doc, base_dir)

    return out

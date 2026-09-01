"""Rendering a filter (design §4.7).

A filter is never run on its own -- it is invoked on the right of a `|` inside
an expression. So the signature leads: it is the whole interface, and it is
what a reader is here to copy.

The not-yet-active notice is not a stylistic hedge. Package-declared filters
are not resolved by the engine today (PLAN.md U14), and a page that presented
one as usable would be telling a reader to type something that fails with an
error naming a registry they have never heard of. The declarations are still
worth documenting -- they are what the author committed to -- but the page has
to say which of the two it is.
"""

from docutils import nodes

from . import blocks, tables
from .docfield import first_paragraph


def not_active_note():
    """Said once per filter, at the top, where it changes what the reader does.

    Consulted from `dv_flow.doc.filter.ACTIVE` rather than hard-coded, so the
    day the engine resolves filters this disappears everywhere at once.
    """
    from dv_flow.doc.filter import ACTIVE

    if ACTIVE:
        return []

    node = nodes.note()
    para = nodes.paragraph()
    para += nodes.strong(text="Not yet resolved by the engine. ")
    para += nodes.Text(
        "This filter is declared, and this page documents that declaration. "
        "Using it in an expression currently fails: the engine does not "
        "register package-declared filters.")
    node += para
    return [node]


def signature(doc):
    """The call, as it is written at a use site."""
    if not doc.signature:
        return []
    para = nodes.paragraph(classes=['dvf-filter-signature'])
    para += nodes.literal(text=doc.signature)
    return [para]


def arguments(doc):
    """The argument table, with the positional slot each one binds to.

    The slot is a column rather than a footnote because arguments bind
    positionally as `$arg0`, `$arg1` -- the name in the declaration is
    documentation, and the position is the interface. A reader who reorders the
    call because the names read better has broken it.
    """
    if not doc.params:
        return []

    headers = ["Argument", "Type", "Binds as", "Description"]
    rows = []
    for param in doc.params:
        rows.append([
            nodes.literal(text=param.name),
            nodes.literal(text=param.type),
            nodes.literal(text=param.define),
            nodes.Text(first_paragraph(param.doc) or param.desc or ""),
        ])
    return [tables.build(headers, rows, classes=['dvf-filter-args'])]


def implementation(doc):
    """The filter body.

    Shown, where a task's `run:` is not: a filter is small enough that its
    source *is* its specification, and the positional `$arg0` binding is
    visible nowhere else.
    """
    if not doc.body:
        return []

    out = []
    para = nodes.paragraph(classes=['dvf-block-title'])
    para += nodes.strong(text="Implementation")
    if doc.impl == 'run':
        para += nodes.Text(" (%s script)" % (doc.shell or 'shell'))
    out.append(para)

    block = nodes.literal_block(doc.body, doc.body)
    block['language'] = 'bash' if doc.impl == 'run' else 'text'
    out.append(block)
    return out


def render(doc, state, base_dir=None, show_source=True):
    out = []
    out += blocks.header(doc)
    out += not_active_note()
    out += signature(doc)
    out += blocks.description(doc, state)
    out += arguments(doc)
    out += implementation(doc)
    if show_source:
        out += blocks.source(doc, base_dir=base_dir)
    return out

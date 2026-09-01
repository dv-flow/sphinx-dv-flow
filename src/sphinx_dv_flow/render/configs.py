"""Rendering a configuration (design §4.7).

A configuration page answers two questions and no others: what does selecting
this change, and what do I type to select it. The selection line comes first
because it is the actionable half, and because a configuration a reader cannot
select is not documentation of anything.
"""

from docutils import nodes

from . import blocks


def selection(doc):
    """`dfm run -c <name> <task>` -- what the reader types.

    Shown as the command rather than as prose about a flag, because a
    configuration is selected at the point of running something and the two
    halves are typed together.
    """
    para = nodes.paragraph(classes=['dvf-config-select'])
    para += nodes.strong(text="Select with ")
    para += nodes.literal(text="dfm run -c %s <task>" % doc.name)
    return [para]


def base(doc):
    if not doc.uses:
        return []
    para = nodes.paragraph()
    para += nodes.strong(text="Extends: ")
    para += nodes.literal(text=doc.uses)
    para += nodes.Text(" — everything that configuration changes applies here "
                       "as well.")
    return [para]


def _xref_list(names, reftype):
    from sphinx import addnodes

    bullet = nodes.bullet_list()
    for name in names:
        item = nodes.list_item()
        para = nodes.paragraph()
        ref = addnodes.pending_xref(
            '', refdomain='dvf', reftype=reftype, reftarget=name,
            refexplicit=False, refwarn=False)
        ref += nodes.literal(text=name)
        para += ref
        item += para
        bullet += item
    return bullet


def changes(doc):
    """What the configuration redefines, by category.

    Names, not expansions. The linked task page documents the task as the
    package loads it by DEFAULT -- which is not what this configuration
    produces. Inlining the override here would put two contradictory
    definitions in one doc set with nothing to say which is which; naming it
    says exactly as much as is true: select this, and that task is different.
    """
    rows = []
    if doc.tasks:
        rows.append(("Tasks", _xref_list(doc.tasks, 'task')))
    if doc.types:
        rows.append(("Types", _xref_list(doc.types, 'type')))
    if doc.overrides:
        bullet = nodes.bullet_list()
        for entry in doc.overrides:
            item = nodes.list_item()
            para = nodes.paragraph()
            para += nodes.literal(text=str(entry))
            item += para
            bullet += item
        rows.append(("Overrides", bullet))
    if doc.imports:
        rows.append(("Adds imports", _plain_list(doc.imports)))
    if doc.fragments:
        # Named rather than expanded: what a fragment contains is only in the
        # package once this configuration is selected, and the docs build
        # loaded the package without it.
        rows.append(("Adds fragments", _plain_list(doc.fragments)))

    if not rows:
        para = nodes.paragraph()
        para += nodes.emphasis(text=(
            "This configuration redefines nothing on its own."))
        return [para]

    return [blocks._field_list(rows)]


def _plain_list(values):
    bullet = nodes.bullet_list()
    for value in values:
        item = nodes.list_item()
        para = nodes.paragraph()
        para += nodes.literal(text=str(value))
        item += para
        bullet += item
    return bullet


def render(doc, state, base_dir=None, show_source=True):
    out = []
    out += blocks.header(doc)
    out += selection(doc)
    out += blocks.description(doc, state)
    out += base(doc)
    out += changes(doc)
    if show_source:
        out += blocks.source(doc, base_dir=base_dir)
    return out

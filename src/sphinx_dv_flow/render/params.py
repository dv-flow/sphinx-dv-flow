"""The parameter table (design §4.2).

This is what replaces the hand-maintained tables, so the columns are chosen for
what a reader has to know before setting a parameter -- not for what happens to
be in the model.
"""

from docutils import nodes

from . import tables
from .docfield import first_paragraph


def _values_text(param):
    """`quiet, normal, full`, or `vlt, vcs, ...` for an open set.

    The trailing ellipsis is not decoration. An open set enumerates the KNOWN
    values without forbidding the rest, and a reader who takes the list as
    exhaustive has been misled by the rendering, not by the flow file.
    """
    if not param.values:
        return ""
    text = ", ".join(str(v.value) for v in param.values)
    return text + ", ..." if param.values_open else text


def _default_nodes(param):
    """The default, with the expression it came from when the two differ.

    Showing only `${{ build }}` is useless to a reader; showing only `opt`
    hides that it tracks a package variable. Both, or neither.
    """
    out = []
    if param.default in (None, ""):
        out.append(nodes.Text("—"))
    else:
        out.append(nodes.literal(text=str(param.default)))
    if param.default_expr:
        out.append(nodes.Text(" from "))
        out.append(nodes.literal(text=param.default_expr))
    return out


def _provenance_nodes(param, task_name):
    """Where the parameter came from, and who changed it.

    A derived task that changed one default must not read as though it declared
    the parameter, so the introducing task is named and the override is a
    separate note (design §4.2).
    """
    if not param.inherited:
        return [nodes.Text("—")]
    out = [nodes.literal(text=param.declared_by)]
    if param.overridden_by and param.overridden_by != param.declared_by:
        out.append(nodes.Text(", changed here"))
    return out


def _table(headers, rows, classes=None):
    """Shared builder -- see `render/tables.py` for why widths are computed."""
    return tables.build(headers, rows, classes=classes)


def param_table(doc, show_provenance=True):
    """All parameters, whether or not they have a flag.

    Every parameter is reachable with `-D`, so a table that showed only the
    ones with flags would leave a reader believing the rest are unreachable.
    That is the point of the block.
    """
    if not doc.params:
        return []

    headers = ["Parameter", "Type", "Default", "Set with"]
    if show_provenance:
        headers.append("Inherited from")
    headers.append("Description")

    rows = []
    for param in doc.params:
        cells = [
            nodes.literal(text=param.name),
            nodes.literal(text=param.type),
            _default_nodes(param),
            nodes.literal(text=param.define),
        ]
        if show_provenance:
            cells.append(_provenance_nodes(param, doc.name))

        desc = first_paragraph(param.doc) or param.desc or ""
        desc_nodes = [nodes.Text(desc)]
        values = _values_text(param)
        if values:
            desc_nodes.append(nodes.Text(" "))
            desc_nodes.append(nodes.emphasis(text="(%s)" % values))
        cells.append(desc_nodes)

        rows.append(cells)

    return [_table(headers, rows, classes=['dvf-params'])]


def value_docs(doc):
    """Per-value documentation, where a value set supplies it.

    A value set is often the only place the meaning of `quiet` versus `normal`
    is written down. Dropping it leaves nothing to replace the prose it was
    meant to replace.
    """
    out = []
    for param in doc.params:
        documented = [v for v in param.values if v.desc]
        if not documented:
            continue

        para = nodes.paragraph()
        para += nodes.strong(text="Values for ")
        para += nodes.literal(text=param.name)
        if param.values_open:
            para += nodes.Text(" (open set — other values are accepted with a "
                               "warning)")
        out.append(para)

        dl = nodes.definition_list()
        for value in documented:
            item = nodes.definition_list_item()
            term = nodes.term()
            term += nodes.literal(text=str(value.value))
            item += term
            definition = nodes.definition()
            definition += nodes.paragraph(text=value.desc)
            item += definition
            dl += item
        out.append(dl)
    return out

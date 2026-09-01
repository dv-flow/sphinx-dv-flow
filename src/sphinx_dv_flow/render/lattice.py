"""Rendering a variant lattice (design §6.3).

Three renderings for three arities, because a product space does not have one
good picture. The 3+ case is the one worth being firm about: no honest 2-D
picture of a 3-D product exists, and every attempt to draw one either drops an
axis or implies an adjacency that is not there. A table is the correct
rendering, not a fallback.
"""

from docutils import nodes

from . import tables
from .blocks import _task_xref

# Marks the cell the bare family name resolves to. "What happens if I don't
# say" is the most common question a family page has to answer, so it is
# answered in the picture rather than only in prose beneath it.
DEFAULT_MARK = " (default)"


def _cell_ref(cell):
    out = [_task_xref(cell.name)]
    if cell.is_default:
        out.append(nodes.Text(DEFAULT_MARK))
    return out


def _mode_note(lattice):
    """What the bare family name means -- a different question from which cell
    is the default."""
    para = nodes.paragraph()
    if lattice.mode == 'all':
        para += nodes.Text("Running ")
        para += nodes.literal(text=lattice.family)
        para += nodes.Text(" runs every cell.")
    elif lattice.mode == 'none':
        para += nodes.Text("Only the cells are addressable; ")
        para += nodes.literal(text=lattice.family)
        para += nodes.Text(" cannot be run on its own.")
    else:
        para += nodes.literal(text=lattice.family)
        para += nodes.Text(" on its own means ")
        default = [c for c in lattice.cells if c.is_default]
        if default:
            para += _task_xref(default[0].name)
        else:
            para += nodes.Text("the first value of each axis")
        para += nodes.Text(".")
    return para


def _row(lattice):
    """One axis: a labelled row of cells."""
    axis = lattice.axis_names[0]
    headers = [axis] + [str(v) for v in lattice.axes[axis]]
    row = ["cell"]
    by_value = {c.bindings.get(axis): c for c in lattice.cells}
    for value in lattice.axes[axis]:
        cell = by_value.get(value)
        row.append(_cell_ref(cell) if cell else nodes.Text("—"))
    return [tables.build(headers, [row], classes=['dvf-lattice'])]


def _grid(lattice):
    """Two axes: a grid with the axes on the margins."""
    row_axis, col_axis, lookup = lattice.grid()

    headers = ["%s \\ %s" % (row_axis, col_axis)] + [
        str(v) for v in lattice.axes[col_axis]]

    rows = []
    for row_value in lattice.axes[row_axis]:
        row = [nodes.strong(text=str(row_value))]
        for col_value in lattice.axes[col_axis]:
            cell = lookup.get((row_value, col_value))
            # A blank rather than a guess: a combination that produced no cell
            # should not be filled in with a neighbour's name.
            row.append(_cell_ref(cell) if cell else nodes.Text("—"))
        rows.append(row)

    return [tables.build(headers, rows, classes=['dvf-lattice'])]


def _table(lattice):
    """Three or more axes: one column per axis, plus the cell name.

    No 2-D picture of an N-D product is honest for N > 2. A table drops
    nothing and implies nothing.
    """
    headers = list(lattice.axis_names) + ["Cell"]
    rows = []
    for cell in lattice.cells:
        row = [nodes.Text(str(cell.bindings.get(axis, "")))
               for axis in lattice.axis_names]
        row.append(_cell_ref(cell))
        rows.append(row)
    return [tables.build(headers, rows, classes=['dvf-lattice'])]


def render(lattice):
    """The lattice, in whichever form its arity calls for."""
    if lattice is None or not lattice.cells:
        return []

    out = [_mode_note(lattice)]
    out += {
        'row': _row,
        'grid': _grid,
        'table': _table,
    }[lattice.form](lattice)

    if lattice.form == 'table':
        note = nodes.paragraph()
        note += nodes.emphasis(text=(
            "Three or more axes: shown as a table because no honest "
            "two-dimensional picture of a higher-dimensional product exists."))
        out.append(note)

    return out

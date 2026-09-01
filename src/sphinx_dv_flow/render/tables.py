"""Table construction shared by every block that emits one.

The one thing this exists to get right is **column widths**. `colspec` takes a
relative weight, and passing 1 for every column tells a fixed-width writer to
divide the line equally -- which in the text builder renders a four-column table
as four one-character columns, with every cell spelled vertically:

    | g | l | n |
    | e | i | e |
    | n | n | e |

That is not a cosmetic problem. The text rendering is the accessible copy of
every diagram (ground rule 5), so a table nobody can read there defeats the rule
it exists to satisfy -- while still passing any test that merely checks the
words are present.

Widths are therefore derived from the content.
"""

from docutils import nodes

# A column has to be wide enough to be worth having, and no column should be so
# wide it starves the rest. Both bounds are in the same relative units as the
# weights themselves.
MIN_WEIGHT = 6
MAX_WEIGHT = 40


def cell(children):
    """A table cell wrapping one node, a list of nodes, or a string."""
    entry = nodes.entry()
    para = nodes.paragraph()
    if isinstance(children, str):
        para += nodes.Text(children)
    elif isinstance(children, (list, tuple)):
        for child in children:
            para += child
    else:
        para += children
    entry += para
    return entry


def _weight(entry) -> int:
    width = len(entry.astext())
    return max(MIN_WEIGHT, min(MAX_WEIGHT, width))


def build(headers, rows, classes=None):
    """A table whose column widths reflect what is actually in them.

    `rows` holds cell contents -- nodes, node lists or strings -- in the same
    order as `headers`.
    """
    header_cells = [cell(h) for h in headers]
    body_rows = [[cell(c) for c in row] for row in rows]

    weights = []
    for column in range(len(headers)):
        widest = _weight(header_cells[column])
        for row in body_rows:
            if column < len(row):
                widest = max(widest, _weight(row[column]))
        weights.append(widest)

    table = nodes.table(classes=classes or [])
    group = nodes.tgroup(cols=len(headers))
    table += group
    for weight in weights:
        group += nodes.colspec(colwidth=weight)

    head = nodes.thead()
    head_row = nodes.row()
    for entry in header_cells:
        head_row += entry
    head += head_row
    group += head

    body = nodes.tbody()
    for row in body_rows:
        body_row = nodes.row()
        for entry in row:
            body_row += entry
        body += body_row
    group += body

    return table

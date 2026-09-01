"""The variant lattice (design §6.3).

A `select:` family's cells are a **product** of axes. That shape is why neither
obvious rendering works: a graph implies edges between cells that do not exist,
and a flat list of names hides the structure entirely -- a reader looking at
`sim-img.vlt.rtl.dbg` through `sim-img.vcs.tlm.opt` cannot see that there are
three independent choices.

So the rendering follows the arity, and the model says which form applies rather
than leaving a renderer to guess:

    1 axis    a labelled row
    2 axes    a grid, axes on the margins
    3+ axes   a table, one column per axis

The 3+ case is the one worth being firm about. There is no honest 2-D picture of
a 3-D product space, and every attempt to draw one either drops an axis or
implies an adjacency that is not there. A table is not a compromise here; it is
the correct rendering.

`default` is marked in every form, because "what happens if I don't say" is the
most common question a family page has to answer.
"""

import dataclasses as dc
import itertools
from typing import Any, Dict, List, Optional


@dc.dataclass
class Cell:
    key: str = ""
    # The full task name -- `<family>.<key>` -- which is what a reader types
    # and what a link has to target.
    name: str = ""
    bindings: Dict[str, Any] = dc.field(default_factory=dict)
    is_default: bool = False

    def to_dict(self):
        return {f.name: getattr(self, f.name) for f in dc.fields(self)}


@dc.dataclass
class Lattice:
    """A family's cells, plus which rendering its arity calls for."""
    family: str = ""
    # 'row' | 'grid' | 'table', chosen by axis count.
    form: str = "table"
    axes: Dict[str, List[Any]] = dc.field(default_factory=dict)
    cells: List[Cell] = dc.field(default_factory=list)
    # 'alias' (the bare name is one cell), 'all' (a gate over every cell), or
    # 'none' (only cells are addressable). This changes what the family NAME
    # means, which is a different question from which cell is the default.
    mode: str = "alias"
    default: Dict[str, Any] = dc.field(default_factory=dict)

    def to_dict(self):
        return {
            'family': self.family,
            'form': self.form,
            'axes': {k: list(v) for k, v in self.axes.items()},
            'cells': [c.to_dict() for c in self.cells],
            'mode': self.mode,
            'default': dict(self.default),
        }

    @property
    def axis_names(self) -> List[str]:
        return list(self.axes.keys())

    def grid(self):
        """`(row_axis, col_axis, {(row_value, col_value): Cell})`.

        Only meaningful for `form == 'grid'`. Returned as a lookup rather than
        a nested list so a renderer can emit an empty marker for a combination
        that produced no cell -- which should not happen, but drawing a blank
        beats drawing the wrong cell.
        """
        if self.form != 'grid':
            return None, None, {}
        row_axis, col_axis = self.axis_names[0], self.axis_names[1]
        lookup = {}
        for cell in self.cells:
            lookup[(cell.bindings.get(row_axis),
                    cell.bindings.get(col_axis))] = cell
        return row_axis, col_axis, lookup


def _form_for(axis_count: int) -> str:
    if axis_count == 1:
        return 'row'
    if axis_count == 2:
        return 'grid'
    return 'table'


def build(task) -> Optional[Lattice]:
    """The lattice for a `select:` family, or None when the task is not one."""
    strategy = getattr(task, 'strategy', None)
    select = getattr(strategy, 'select', None) if strategy is not None else None
    if select is None:
        return None

    axes = {name: list(values)
            for name, values in (getattr(select, 'axes', None) or {}).items()}
    if not axes:
        return None

    default = dict(getattr(select, 'default', None) or {})
    family = getattr(task, 'name', '')

    cells = []
    for key, bindings in (getattr(select, 'cells', None) or {}).items():
        bindings = dict(bindings)
        cells.append(Cell(
            key=key,
            name="%s.%s" % (family, key),
            bindings=bindings,
            # A binding map default names exactly one cell. Under 'all' or
            # 'none' no cell is the default, and marking one would answer a
            # question the author explicitly declined to answer.
            is_default=(bool(default) and
                        all(bindings.get(a) == v for a, v in default.items()))))

    return Lattice(
        family=family,
        form=_form_for(len(axes)),
        axes=axes,
        cells=cells,
        mode=getattr(select, 'mode', 'alias') or 'alias',
        default=default)


def cell_names(task) -> List[str]:
    """Every addressable cell name, for indexing and cross-referencing."""
    lattice = build(task)
    return [c.name for c in lattice.cells] if lattice else []

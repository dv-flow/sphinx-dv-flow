"""The variant lattice (design §6.3).

A family's cells are a product of axes, and that shape is why neither obvious
rendering works: a graph implies edges between cells that do not exist, and a
flat list of names hides the structure entirely.
"""

import os

import pytest

from dv_flow.doc.diagram import lattice as lattice_mod
from dv_flow.doc.loader import load_project


@pytest.fixture(scope="module")
def variants():
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "variants")
    result = load_project(root)
    assert result.ok
    return result


def _lattice(variants, name):
    return lattice_mod.build(variants.pkg.task_m[name])


# ------------------------------------------------------ form follows arity

def test_one_axis_is_a_row(variants):
    assert _lattice(variants, "variants.OneAxis").form == 'row'


def test_two_axes_are_a_grid(variants):
    assert _lattice(variants, "variants.TwoAxis").form == 'grid'


def test_three_axes_are_a_table(variants):
    """No honest 2-D picture of a 3-D product space exists. Every attempt
    either drops an axis or implies an adjacency that is not there, so a table
    is the correct rendering rather than a fallback."""
    assert _lattice(variants, "variants.ThreeAxis").form == 'table'


def test_a_task_with_no_select_has_no_lattice(data_dir):
    result = load_project(os.path.join(data_dir, "matrix"))
    # A `matrix:` fans a task out; it is not a catalog of addressable cells.
    assert lattice_mod.build(result.pkg.task_m["matrix.Sweep"]) is None


# ------------------------------------------------------------------- cells

def test_cells_are_the_cartesian_product(variants):
    assert len(_lattice(variants, "variants.ThreeAxis").cells) == 8


def test_a_cell_carries_the_name_a_reader_types(variants):
    """`<family>.<key>` -- what goes on a command line, and what a link has to
    target."""
    names = {c.name for c in _lattice(variants, "variants.OneAxis").cells}
    assert names == {"variants.OneAxis.vlt", "variants.OneAxis.vcs"}


def test_a_cell_carries_its_bindings(variants):
    cells = {c.key: c for c in _lattice(variants, "variants.TwoAxis").cells}
    assert cells["rtl.dbg"].bindings == {"view": "rtl", "build": "dbg"}


# ----------------------------------------------------------------- default

def test_an_implicit_default_is_the_first_of_each_axis(variants):
    lattice = _lattice(variants, "variants.OneAxis")
    default = [c for c in lattice.cells if c.is_default]
    assert [c.key for c in default] == ["vlt"]


def test_an_explicit_default_is_marked(variants):
    """"What happens if I don't say" is the most common question a family page
    has to answer, so it is answered in the picture."""
    lattice = _lattice(variants, "variants.TwoAxis")
    default = [c for c in lattice.cells if c.is_default]
    assert [c.key for c in default] == ["tlm.opt"]


def test_exactly_one_cell_is_the_default(variants):
    for name in ("variants.OneAxis", "variants.TwoAxis", "variants.ThreeAxis"):
        marked = [c for c in _lattice(variants, name).cells if c.is_default]
        assert len(marked) == 1, name


# -------------------------------------------------------------------- grid

def test_the_grid_lookup_covers_every_combination(variants):
    lattice = _lattice(variants, "variants.TwoAxis")
    row_axis, col_axis, lookup = lattice.grid()
    assert row_axis == "view" and col_axis == "build"
    for row in lattice.axes[row_axis]:
        for col in lattice.axes[col_axis]:
            assert (row, col) in lookup


def test_a_non_grid_lattice_has_no_grid(variants):
    row_axis, col_axis, lookup = _lattice(variants, "variants.ThreeAxis").grid()
    assert row_axis is None and lookup == {}


# ------------------------------------------------------------------- mode

def test_mode_is_reported(variants):
    """What the bare family name MEANS -- a different question from which cell
    is the default."""
    assert _lattice(variants, "variants.OneAxis").mode == 'alias'


def test_cell_names_are_available_for_indexing(variants):
    names = lattice_mod.cell_names(variants.pkg.task_m["variants.TwoAxis"])
    assert len(names) == 4
    assert all(n.startswith("variants.TwoAxis.") for n in names)


def test_the_lattice_is_serializable(variants):
    import json
    json.dumps(_lattice(variants, "variants.TwoAxis").to_dict())

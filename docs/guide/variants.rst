########
Variants
########

A ``select:`` family declares a **catalog**. Each cell is a first-class task
named ``<family>.<key>``, built only when something asks for it and shared when
two consumers ask for the same one.

That is a different thing from ``strategy: matrix``, which fans a task out —
running it runs every combination. The documentation keeps them apart: a matrix
draws a ``for each {...}`` region, a family draws its lattice. "One of" and "for
each" are different statements and must not render alike.

Three shapes for three arities
==============================

Cells are a *product* of axes, so there is no single good picture:

**One axis** — a labelled row.

**Two axes** — a grid, axes on the margins.

**Three or more** — a table, one column per axis, plus the cell name.

The last is worth being firm about. There is no honest two-dimensional picture
of a three-dimensional product space: every attempt either drops an axis or
implies an adjacency that is not there. A table drops nothing and implies
nothing, so it is the correct rendering rather than a fallback — and the page
says so, rather than leaving a reader to wonder why this family looks different.

What the bare name means
========================

Two separate questions, and the page answers both:

**Which cell is the default** — marked ``(default)`` in every form. "What
happens if I don't say" is the most common question a family page has to answer.

**What the family name does** — set by ``default:``:

``{axis: value, ...}``
    The family is an alias for one cell.

``all``
    Running the family runs every cell.

``none``
    Only the cells are addressable; the family cannot be run on its own.

Omitting ``default:`` means the first value of each axis.

Linking to a cell
=================

.. code-block:: rst

    :dvf:task:`sim-img.vlt.rtl`

Cells resolve to their **family's** page. They get no page of their own —
folding them into the family is the point of the variant view, and a 3×4 lattice
given twelve pages would bury the family that explains what the cells mean.
Without registering the names, though, nothing in the doc set could link to a
cell at all, so every cell name is a resolvable target pointing at the family.

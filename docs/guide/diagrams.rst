########
Diagrams
########

Declared, not elaborated
========================

There are two graphs you could draw for a flow, and the difference matters more
than it looks.

============================ ============================= =============================
\                            **Declared**                  **Elaborated**
============================ ============================= =============================
Source                       ``subtasks`` + ``needs``      a full graph build
``matrix:`` / ``select:``    one region, labelled by axes  one node per combination
``iff:``                     a guard on the edge           resolved away
Cost                         no graph build                full elaboration per diagram
Depends on the environment   no                            yes
Default                      **yes**                       opt-in
============================ ============================= =============================

**The declared view is the default, and that is the main claim these diagrams
make.** An elaborated diagram of a 3×4×2 matrix is twenty-four near-identical
boxes that teach a reader nothing about the structure they need to modify. The
parameterized view — one region labelled ``for each {sim: [...], test: [...]}``
— is both smaller and closer to what the author actually wrote.

It is also reproducible. An elaborated graph is one machine's expansion of one
configuration, so two people can generate different pictures of the same flow
and both be right.

The activity mapping
====================

A compound task maps onto a UML activity diagram, and stating the mapping
precisely is what makes diagrams consistent across a whole package:

============================== ==============================================
Flow construct                 Rendering
============================== ==============================================
Subtask (leaf)                 rounded box, ``desc`` as tooltip
Subtask (compound)             subroutine box, links to its own page
``needs:``                     solid arrow
Inferred dataflow              **dashed** arrow, labelled with the item type
Independent subtasks           no edge between them
``strategy: matrix``           dashed region, ``for each {...}``, body once
``select:`` family             dashed region, ``one of {...}``
``iff:``                       guard label on the incoming edge
============================== ==============================================

Inferred edges are not declarations
===================================

A ``needs:`` edge says *after*. It does not say *consumes what it produced*.

Matching a producer's ``produces`` against a consumer's ``consumes`` recovers
the object flow, which is what an engineer tracing a verification flow actually
wants. It is genuinely an inference — two tasks can match without the author
ever intending a data dependency — so those edges are drawn dashed, marked
``inferred`` in the accompanying table, and can be turned off:

.. code-block:: rst

    .. dvf:flowdiagram:: build
       :no-dataflow:

An inference presented as a declaration is a lie, which is the whole reason for
the distinction.

Depth and size
==============

``:depth:`` defaults to 1. A compound's own body is its interface; its
subtasks' bodies are theirs, and they are on their own pages. A nested compound
renders as one box that links there — which is also what makes a diagram a
navigation surface rather than a wall.

Past ``dvflow_diagram_max_nodes`` (default 40) the diagram is capped and a
warning records how many nodes were dropped. Silent truncation would be worse
than either an unreadable diagram or an explicit note: a capped diagram that
reads as complete tells the reader something false and gives them no way to
notice.

Every diagram has a textual twin
================================

No information exists only in a picture. Each diagram is emitted alongside a
table of its edges — with inferred ones still marked — or, for a diagram with no
edges, a sentence describing its region. Build with ``-b text`` and the
relationships are all still there.

This is not only an accessibility measure, though it is that. It also means a
diagram's content is diffable, greppable, and reviewable, which a rendered
picture is not.

The class view
==============

.. code-block:: rst

    .. dvf:inheritance:: proj.sim
       :descendants:

Tasks form a single-inheritance hierarchy through ``uses:``, and so do types.
The useful part is the attribute compartment: each box lists **the parameters
that level introduces**, not the merged set. A reader sees at a glance that
``top`` came from the simulator base and ``trace`` from the project task — the
same provenance the parameter table carries, made spatial.

A level that only changes a default shows the parameter as ``name = value``, and
one that overrides without setting a value shows ``name (override)``. Both say
"this level changed one thing" rather than "this level declared this".

``requires:`` is drawn as a realization, from the level that imposed it —
showing the accumulated set would attribute an obligation to the wrong level,
which is exactly what the diagram exists to get right.

Ancestors are always drawn; descendants are opt-in and bounded, because a
widely-used base has too many.

What is not drawn yet
=====================

``control:`` constructs (``if``, ``match``, ``while``) have no decision or loop
regions. The information is not in the loaded model — the engine parses
``control:`` onto the task definition but does not carry it onto the resolved
task — so there is nothing to draw from.

That gap is a confirmed engine bug rather than a missing feature here: the same
omission means a ``control:`` task ignores its condition and runs its ``body:``
unconditionally at execution time. It is recorded in dv-flow-mgr's own suite as
``tests/unit/test_control_flow_from_flow_file.py``, and these regions arrive
once it is fixed. See ``PLAN.md`` §5 U13.

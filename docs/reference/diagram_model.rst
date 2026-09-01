#############
Diagram Model
#############

A diagram is built as data and rendered separately. The split is what makes
diagram *content* testable: "does the matrix body appear once" is a question
about the model, and answering it against rendered SVG would be answering a
different and much harder question badly.

``dvflow-doc dump`` includes the model for any task that has one.

Nodes
=====

``id``
    Stable within a diagram, derived from the object's name. An id keyed on
    position would churn every golden when a sibling is added.

``label``
    What is drawn on the box — a subtask's *local* name.

``ref``
    The object this node links to, which is **not** always what it is labelled.
    A subtask written ``uses: pkg.Build`` is labelled ``inner`` but the page a
    reader wants is ``pkg.Build``'s. Matching a link on the label would find
    nothing and the diagram would quietly lose its navigation.

``shape``
    ``action`` (a leaf), ``call`` (a compound drawn as one box), ``class``.
    The ``call`` shape is what says "there is more inside this one"; without it
    a collapsed compound is indistinguishable from a leaf.

``guard``
    An ``iff:`` condition. It rides on the node and renders on the *incoming
    edge*, because a guard says when a step is reached — it is not a branch
    point, and drawing it as one would imply an alternative path that does not
    exist.

``stereotypes``, ``abstract``, ``attributes``
    UML decorations. ``attributes`` holds the parameters introduced at that
    level, not the merged set.

Edges
=====

``kind``
    ``needs`` (control flow), ``dataflow`` (object flow), ``uses``
    (generalization), ``requires`` (realization).

``inferred``
    **Load-bearing.** True when the edge was recovered by matching rather than
    declared. Rendered dashed, and marked in the textual twin as well — the
    table is the accessible copy, and dropping the distinction there would
    leave an inference reading as a declaration for exactly the readers who
    cannot check it against the picture.

Regions
=======

``kind``
    ``expansion`` (``for each``) or ``choice`` (``one of``). A fan-out and a
    selection are different statements and must not render alike.

``label``
    Names each axis with its values bracketed. Without brackets the axes run
    together and the reader cannot see where one ends — and the axis structure
    is the entire reason for drawing a region.

Truncation
==========

``truncated``
    **Load-bearing.** ``{reason, omitted}`` when a cap was applied. A capped
    diagram must never read as a complete one, so this drives a visible warning
    rather than only appearing in the data.

Emptiness
=========

``is_empty()`` is true for no nodes at all, and also for **a single node with
no edges and no region** — one box, drawn alone, showing a name the heading
already gave. That is not a diagram, and rendering it costs the reader
attention while telling them nothing.

A single node *inside a region* is different and is drawn: the region label is
the content, not the box.

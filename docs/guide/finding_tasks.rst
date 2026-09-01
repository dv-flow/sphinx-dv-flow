##############
Finding a Task
##############

An alphabetical list of task names is the index a documentation tool produces
when nobody asked what a reader is actually looking for. The questions worth
answering are the ones a flow library makes hard, and they are all *reverse*
directions — the flow file states each relationship exactly one way.

The indices
===========

``dvf-produced``
    Tasks grouped by the item type they produce. *"I have a consumer — what
    makes one of these?"*

``dvf-consumed``
    Tasks grouped by the item type they consume. *"I have an ObjFile — what can
    take one?"*

``dvf-tags``
    Tasks grouped by the tags they carry. *"What is deprecated in this
    library?"* — a question a maintainer asks about code they did not write,
    and one with no other answer short of reading every page.

``dvf-tasks``, ``dvf-types``
    Everything by name, grouped by package. The conventional index, kept
    because sometimes you do just want the list.

Link to them with ``:ref:`dvf-produced``` and so on.

Qualified requirements stay separate
====================================

A task consuming ``{type: std.FileSet, filetype: verilogSource}`` is listed with
that qualifier rather than merged into "takes any FileSet". It is not an answer
to the general question, and presenting it as one sends a reader down a path
that will not connect.

Visibility is respected
=======================

An index never lists an internal or ``local`` task, and never a task with no
page. An entry pointing at a page that does not exist is worse than no entry,
and an index that names something a reader cannot address is worse still.

That also means deprecated tasks are absent from the indices when they are
absent from the package listing — which is the same rule, applied in the same
place, for the same reason.

The maps
========

Sometimes the answer is better drawn than listed:

.. code-block:: rst

    .. dvf:dataflow::                    # the whole package
    .. dvf:dataflow:: proj.ObjFile       # centred on one type
    .. dvf:packagediagram::              # provided and required interfaces

The package map is emitted automatically at the top of a package that has **no
runnable tasks** — a library's landing page should open with what connects to
what, because that is why a reader came. Where there are entry points, they come
first instead; someone who can run something wants to know that before they read
a type map. Force it either way with ``:map:``.

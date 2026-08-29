#####
Roles
#####

``:dvf:task:``
==============

.. code-block:: rst

    :dvf:task:`proj.sim`
    :dvf:task:`sim`

The package prefix is optional when the leaf name is unambiguous. Fully
qualified names are tried first, so an exact name can never be shadowed by a
leaf match; an ambiguous leaf resolves to neither, rather than to whichever
document happened to be read first.

``:dvf:type:``
==============

Cross-reference a data type. Item types appearing in ``produces:`` and
``consumes:`` are emitted as these references automatically, so the dataflow
blocks link to the types they name.

``:dvf:package:``
=================

Cross-reference a package.

When a reference does not resolve
=================================

A reference **you wrote** warns, with suggestions:

.. code-block:: text

    WARNING: dvf:task reference target not found: proj.smi.
        Did you mean proj.sim?

An ambiguous leaf name says so, and names the candidates — because the fix is to
qualify it:

.. code-block:: text

    WARNING: dvf:task reference target not found: sim.
        'sim' is ambiguous -- qualify it: a.sim, b.sim

A reference the extension **generated** — a type named in a ``produces:``
entry — does not warn when it dangles. A doc set covering one package of several
would otherwise emit noise proportional to the size of the flow, which is how a
warning stream stops being read. Sphinx's ``nitpicky`` mode still reports them
for anyone who wants that.

Either way the reference degrades to literal text, so the name stays on the page
even without a link to follow.

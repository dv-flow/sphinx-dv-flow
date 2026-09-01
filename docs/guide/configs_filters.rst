##############################
Configurations and Filters
##############################

Both are declared on a package rather than inside a task, and both are things a
reader selects or invokes by name. That is what makes them documented objects
rather than package-page prose: a name someone types is a name something else
should be able to link to.

Configurations
==============

A configuration is a named way to load a package. What a reader needs from one is
not how it is implemented but two things: what it changes, and what to type to
get it.

.. code-block:: yaml

    configs:
    - name: debug
      desc: Build with debug output
      doc: |
        Replaces the build step with one that says what it is doing.
      tasks:
      - override: Build
        uses: std.Message
        with:
          msg: "debug build"

Rendered, that leads with the selection command — ``dfm run -c debug <task>`` —
and then names what the configuration redefines: tasks, types, imports,
fragments, package overrides, and the configuration it extends.

**Names, not expansions.** The linked task page documents the task as the
package loads it by *default*, which is not what this configuration produces.
Inlining the override here would put two contradictory definitions in one
documentation set with nothing to say which is which. Naming it says exactly as
much as is true: select this, and that task is different.

The same reasoning covers an added fragment. What it contains is only in the
package once the configuration is selected, and the documentation build loaded
the package without it — so the fragment is named and not expanded.

Configurations have no visibility model. Anyone who can run the flow can select
any of them, so hiding one would not make it unreachable — only undiscoverable.

.. note::

   Configuration pages do not show "parameters this configuration fixes".
   ``ConfigDef.params`` is typed as a list while the merge that consumes it
   implements only the map form, so neither spelling does anything upstream. A
   page showing them would be describing a mechanism that does not run, which is
   worse than saying nothing — the reader cannot tell.

Filters
=======

A filter is a named transformation, invoked on the right of a ``|`` inside an
expression. It is never run on its own, so the signature is the whole interface:

.. code-block:: yaml

    filters:
    - export: by_arch
      desc: Select inputs matching a target architecture
      with:
        arch:
          type: str
          desc: Architecture to match.
      expr: "input[] | select(input.arch == $arg0)"

which documents as ``${{ inputs | by_arch(arch) }}``, an argument table, and the
implementation.

**Arguments bind positionally.** ``$arg0``, ``$arg1`` — the name in the
declaration is documentation and the position is the interface, so the table
shows both. A reader who reorders a call because the names read better has
broken it.

**The implementation is shown**, where a task's ``run:`` is not. A filter is
small enough that its source is its specification, and the positional binding is
visible nowhere else.

Visibility follows the same rules as tasks, read off the same words: ``export``
and ``root`` are published, an unscoped filter is package-internal and appears
only under ``:internal:``, and a ``local`` filter never appears — a reader
outside the fragment cannot name it.

Filters declared in fragments are found too. Organizing them into one is the
obvious thing to do — ``std`` does exactly that — and a package that did would
otherwise document none of them.

.. warning::

   The engine does not yet resolve package-declared filters. A ``Package``
   carries no ``filters``, so the registration in ``TaskGraphBuilder`` never
   fires and no evaluator is given a registry; using one in an expression fails
   with "no filter registry configured".

   Filter pages therefore say so. The declarations are real and worth
   documenting — they are what the author committed to — but a page presenting
   them as usable today would be telling a reader to type something that fails.

On the package page
===================

Both appear on ``dvf:autopackage`` by default, after the tasks, in the order
Filters then Configurations.

By default, unlike types — and for a reason. A type has somewhere else to live:
its own page, the type index, a cross-reference from every ``produces:`` entry
that names it. A configuration has none of those. If the package page does not
mention it, a reader has no way to discover that ``-c ci`` is something they may
type.

``:configs: false`` and ``:filters: false`` turn them off; ``dvf:autoconfig`` and
``dvf:autofilter`` document one at a time, or all of them somewhere else.

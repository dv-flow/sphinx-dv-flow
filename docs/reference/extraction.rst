####################
Extraction Contract
####################

``dv_flow.doc`` turns a loaded DV Flow project into plain data. One document per
documented object, JSON-serializable, produced by the extractors and consumed by
the renderers. **Renderers never touch** ``Task`` **objects.**

That seam is the one architectural decision in this project that is expensive to
reverse, and it buys three things: the extractor is testable as data without
standing up a Sphinx build, ``dvflow-doc dump`` has something real to print, and
there is a clean path if extraction later moves upstream into
``dfm show task --json``.

.. note::

   ``dv_flow.doc`` does not import Sphinx — or docutils, since an extractor that
   builds docutils nodes is a renderer whatever it imports. This is enforced by
   a test that walks every submodule in a subprocess, not by convention.

Inspecting it
=============

.. code-block:: shell

    dvflow-doc dump -r path/to/project              # package + every task
    dvflow-doc dump sim -r path/to/project          # one task
    dvflow-doc dump -r path/to/project --internal   # include internal tasks

This is the same document the directives render, which makes it useful for more
than debugging: a disagreement between a rendered page and this output is a
renderer bug, and there is no third place to look.

Where the facts come from
=========================

Nothing is re-derived. Each fact has exactly one source in the engine:

=========================== =========================================
Fact                        Engine contract
=========================== =========================================
Merged parameters           ``collect_task_params()``
Value sets                  ``collect_param_value_sets()``
Command-line options        ``resolve_task_cli()``
The CLI view (root tasks)   ``build_usage_info()``, carried verbatim
Inheritance chain           ``iter_uses_chain()``
Resolved defaults           throwaway ``TaskGraphBuilder``
=========================== =========================================

Where the engine has no contract for something documentation needs, it is added
upstream rather than reached around. The alternative is a second model of the
flow that drifts from the first, with the documentation being the half nobody
notices is wrong.

Task document
=============

``kind``
    Which of the documentation kinds the task classified as: ``root``,
    ``library``, ``abstract``, ``compound``, ``variants``, ``variant-cell`` or
    ``internal``. Classification is a cascade, first match wins.

``scope``
    The declared visibility: ``root``, ``export``, ``local``. This doubles as
    the documentation-audience model — what is published stops being a
    documentation decision and becomes a consequence of a declaration the author
    already had to make.

``facets``
    Annotations that describe a task without replacing its kind: ``pytask``,
    ``shell``, ``elaborate``, ``requires``, ``needs``, ``also-library``. Keeping
    these separate from ``kind`` is what stops the cascade from growing a branch
    per combination.

``uses_chain``
    Names along ``uses:``, most-derived first, **excluding the task itself**.

``usage``
    ``build_usage_info()`` verbatim, present only for root tasks. Verbatim
    because ``dfm show task --usage`` and the rendered option list have to
    answer the same question the same way.

``consumes`` / ``consumes_declared``
    ``consumes`` is what the engine will act on, **including its default**.
    ``consumes_declared`` says whether anyone actually declared it. These are
    different statements and a renderer must not conflate them: presenting the
    engine's default as an authored contract states something the author never
    said.

    An inherited declaration *is* a declaration — the reader is subject to that
    contract. An inherited default is not.

``produces``
    What the task *may* produce, not what it always does. Say so once in the
    heading rather than hedging each row.

Parameters
==========

Each parameter carries:

``default`` / ``default_expr``
    ``default`` is the **resolved** value where resolution was available;
    ``default_expr`` is the source expression, present only when the two
    differ. Showing only ``${{ build }}`` is useless to a reader; showing only
    ``opt`` hides that it tracks a package variable.

``declared_by`` / ``overridden_by`` / ``inherited``
    ``declared_by`` is where the parameter was **introduced** — the furthest
    task along ``uses:`` that declares it — not the nearest one that mentions
    it. Re-declaring a parameter to change one default is the common case, and
    crediting the derived task with the declaration would make it read as if it
    had redeclared the world. ``overridden_by`` names the nearest task that
    re-declared it, so a page can say "inherited from ``Base``, default changed
    here".

``values`` / ``values_open``
    An **open** value set enumerates the *known* values without forbidding the
    rest. Rendering one as exhaustive is a lie the reader cannot detect, so
    ``values_open`` must reach the renderer.

``cli``
    Present only when the parameter actually has a flag, which is decided by
    ``resolve_task_cli`` — not by whether a ``cli:`` declaration exists. A
    derived task that removed an inherited flag with ``cli: false`` has a
    declaration and no flag; only one of those is true for the reader. Hidden
    options are extracted, and omitted by the renderer rather than here.

``define``
    The ``-D`` form, present for **every** parameter. That is the point: every
    parameter is reachable, not only the ones that were given flags.

.. note::

   There is deliberately no ``required`` field. The engine substitutes a type
   default (``""``, ``0``, ``[]``) at load, so "declared without ``value:``" is
   erased before anything can read it — and a task whose parameter has no
   authored default still runs. Marking such a parameter required would promise
   enforcement that does not exist.

Diagnostics
===========

Loading returns a result, never an exception. A malformed flow file produces
error markers carrying a ``file:line``, which the Sphinx layer forwards as
located warnings. Raising through a directive would turn one bad flow file into
a build with no output at all.

An **unresolvable expression** is different from a **malformed file**: the first
degrades to the declared source text and warns, the second fails the build. A
docs build must never fail because a default happened to reference something
unresolvable in the documentation environment.

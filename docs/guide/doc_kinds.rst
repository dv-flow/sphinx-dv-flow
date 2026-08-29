##############
Task Doc Kinds
##############

A task's *kind* selects a page template. It is decided by what the task is, not
by which directive you wrote — so a page cannot describe a task as something it
is not.

The cascade
===========

First match wins:

.. code-block:: text

    abstract: true              -> Abstract / extension point
    strategy.select present     -> Variant family
    select_bindings present     -> (suppressed; folded into its family)
    subtasks non-empty          -> Compound / sub-flow
    scope: root                 -> Root / command-line interface
    scope: export               -> Library / composable building block
    otherwise                   -> Internal (excluded by default)

The order is the substance, not an implementation detail:

- **abstract beats root.** An abstract task is an extension point even when it
  declares a scope. What the reader needs is "derive from this", and running it
  is not available anyway.
- **a variant family beats compound.** A family may have a body, but what a
  reader addresses is the set of cells.
- **a cell is suppressed**, folded into its family's page. Giving each cell of a
  3×4 lattice its own page would bury the family that explains them.
- **compound beats root.** The sub-flow is the interesting content; scope
  survives as a badge, so nothing is lost.

Facets
======

Facets annotate a task without changing its kind: ``pytask``, ``shell``,
``elaborate``, ``requires``, ``needs``, ``also-library``. Keeping them separate
is what stops the cascade from growing a branch per combination.

Root — the command-line interface
=================================

Answers *how do I run this, and what can I pass it?* Synopsis, an option list
(so the flags land in the index and ``:option:`` references resolve), then every
parameter without a flag shown with its ``-D`` form — because all of them are
reachable, not just the ones given flags.

Library — the composable building block
=======================================

Answers *what do I get if I use this?* The distinguishing content is the
dataflow contract: ``consumes`` and ``produces`` are the type signature of a
flow task. Parameters carry provenance, so a task that changed one default reads
as exactly that rather than as if it redeclared the world.

Abstract — the extension point
==============================

Answers *how do I derive from this?* No synopsis, ever — not even when the task
declares ``scope: root``, because it cannot be run. Parameters are split into
what an implementation must set and what it may override; ``requires:`` is shown
as the contract a deriver has to satisfy; and known implementations are listed,
which nothing in the flow file answers because ``uses:`` points the other way.

Data type — the vocabulary
==========================

Most of a type page points the other way from the declarations: who produces
this, who consumes it, what derives from it. A type nothing touches says so,
rather than rendering an empty section that reads as "not documented yet".

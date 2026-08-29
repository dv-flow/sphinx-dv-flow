##########
Quickstart
##########

Point the extension at a flow project and it generates the reference pages.

1. Enable it
============

.. code-block:: python

    # conf.py
    extensions = [
        "sphinx_dv_flow",
    ]

If your ``docs/`` directory sits inside the flow project, that is all the
configuration needed — the extension searches upward for the flow file, the same
way ``dfm`` does. Otherwise, say where the project is:

.. code-block:: python

    dvflow_root = "../my-project"

2. Document a task
==================

.. code-block:: rst

    .. dvf:autotask:: sim

The page you get depends on what the task *is*, not on which directive you
wrote. A ``root:`` task renders as a command-line interface — synopsis, options,
the ``-D`` form for every parameter that has no flag. An ``export:`` task
renders as a composable building block — parameters with provenance, and the
dataflow contract a caller has to satisfy.

3. Document a whole package
===========================

.. code-block:: rst

    .. dvf:autopackage::

This documents what the package publishes: ``root:`` and ``export:`` tasks.
Package-internal tasks are excluded unless you ask for them; ``local:`` tasks are
excluded always, because a fragment-scoped name is not something a reader can
address.

That mapping is the single most useful thing the extension does. *What is
published* stops being a documentation decision and becomes a consequence of a
declaration the author already had to make.

4. Link to it
=============

.. code-block:: rst

    See :dvf:task:`proj.sim` for the simulation task.

The package prefix is optional when the leaf name is unambiguous, so
:literal:`:dvf:task:\`sim\`` works inside a package's own documentation.

What you did not have to do
===========================

Nothing above restates a fact that is already in the flow file. The parameter
table, the defaults, the accepted values, the inheritance chain and the
command-line options all come from the project — which means they are right
today and stay right when the flow file changes.

The parts worth knowing about
=============================

**Defaults are resolved.** A parameter declared ``value: "${{ build }}"``
renders as ``[default: opt — from ${{ build }}]``. Showing only the expression
is useless to a reader; showing only the value hides that it tracks a package
variable.

**Open value sets are marked.** A set declared ``{of: [...], open: true}``
renders with a trailing ellipsis and a note. An unlisted value warns rather than
failing, and a reader who takes the list as exhaustive has been misled.

**Inherited parameters name their origin.** A task that derives from a base and
changes one default reads as exactly that, rather than as though it declared
every parameter itself.

**Undeclared is not the same as declared-empty.** A task that says nothing about
``consumes:`` renders as *not declared — accepts all inputs*, visually distinct
from ``consumes: none``. The engine defaults ``consumes``, and presenting that
default as an authored contract would state something the author never said.

**A broken flow file fails with a location.** The warning points at
``flow.yaml:12``, not at the ``.rst`` that referenced the task. An expression
that cannot be resolved in the documentation environment only warns, and the
page falls back to the declared source text — a docs build should not fail
because of something it could not evaluate.

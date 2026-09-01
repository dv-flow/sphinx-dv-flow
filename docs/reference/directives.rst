##########
Directives
##########

``dvf:autotask``
================

.. code-block:: rst

    .. dvf:autotask:: <name>

Documents one task. ``<name>`` may be fully qualified (``proj.sim``) or the
unqualified leaf (``sim``) when that is unambiguous within the package.

Which page you get is decided by what the task is, not by the directive:

============================ ==========================================
Task                         Page
============================ ==========================================
``scope: root``              Command-line interface (§4.1)
``scope: export``            Composable building block (§4.2)
``root`` **and** ``export``  Both — the CLI view, then "Using this task
                             in a flow"
============================ ==========================================

Options
-------

``:root:``
    Flow project to load, overriding ``dvflow_root``. Relative paths resolve
    against the documentation source directory — a doc set that covers more
    than one project needs this.

``:config:``
    Package configuration to load, overriding ``dvflow_config``.

``:no-source:``
    Omit the ``Defined in flow.yaml:NN`` line.

``:noindex:``
    Render the task without registering it in the domain. Use this for a second
    presentation of a task documented elsewhere; without it the two pages both
    claim the name and every reference to it becomes a coin flip.

``dvf:autopackage``
===================

.. code-block:: rst

    .. dvf:autopackage::

Documents every task the package publishes, in declaration order.

Inclusion follows visibility, which the engine already models:

============= ================================= ===================
Scope         Meaning                           Documented
============= ================================= ===================
``root``      Executable entry point            Yes
``export``    Visible to other packages         Yes
*(none)*      Package-internal                  Only ``:internal:``
``local``     Fragment-only                     Never
============= ================================= ===================

``local`` is never documented, whatever the options say: a fragment-scoped name
is not addressable by a reader, so a page about it could not tell them anything
they could act on.

Options
-------

``:root:``, ``:config:``, ``:no-source:``
    As for ``dvf:autotask``.

``:internal:``
    Include package-internal tasks. Accepts ``true``/``false``; bare
    ``:internal:`` means true. Overrides ``dvflow_internal``.

``:configs:``, ``:filters:``
    Include configurations and filters. Both default to **true**, unlike
    ``:types:`` — see :doc:`../guide/configs_filters` for why.

``dvf:autoconfig``
==================

.. code-block:: rst

    .. dvf:autoconfig::            # every configuration
    .. dvf:autoconfig:: debug      # one

Documents a package configuration: how to select it, what it extends, and what
it redefines. See :doc:`../guide/configs_filters`.

Options
-------

``:root:``, ``:config:``, ``:no-source:``, ``:noindex:``
    As for ``dvf:autotask``.

``:members:``, ``:exclude:``
    Glob patterns over configuration names.

``dvf:autofilter``
==================

.. code-block:: rst

    .. dvf:autofilter::            # every documented filter
    .. dvf:autofilter:: by_arch    # one

Documents a filter: its signature as written at a call site, its arguments and
the positions they bind to, and its implementation.

``local`` filters are refused even when named explicitly — a reader outside the
fragment cannot invoke one, so documenting it would publish a call that cannot
be written.

Options
-------

``:root:``, ``:config:``, ``:no-source:``, ``:noindex:``
    As for ``dvf:autotask``.

``:internal:``
    Include unscoped (package-internal) filters.

``:members:``, ``:exclude:``
    Glob patterns over filter names.

Roles
=====

``:dvf:task:``
    Cross-reference a documented task. The package prefix is optional when the
    leaf name is unambiguous.

``:dvf:type:``
    Cross-reference a data type. Item types in ``produces:`` and ``consumes:``
    are already emitted as these references; the targets they resolve to arrive
    with the type directive.

``:dvf:package:``
    Cross-reference a package.

``:dvf:config:``, ``:dvf:filter:``
    Cross-reference a configuration or a filter.

An unresolved reference degrades to literal text rather than warning, so the
name stays on the page even with no link to follow. A reference you *wrote*
warns, with suggestions; a reference the extension generated does not. See
:doc:`roles`.

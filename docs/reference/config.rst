#############
Configuration
#############

All settings are optional. The common case — one flow project, documented from a
``docs/`` directory inside it — needs no configuration at all.

``dvflow_root``
===============

:Type: ``str`` or ``None``
:Default: ``None``

The flow project to document. Relative paths resolve against the documentation
source directory, not the working directory, so a build does not depend on where
it was invoked from.

When unset, the source directory itself is used. Because the loader searches
upward for the flow file — exactly as ``dfm`` does — that finds the project from
anywhere inside it.

A directive's ``:root:`` option overrides this, which is how one doc set covers
several projects.

``dvflow_config``
=================

:Type: ``str`` or ``None``
:Default: ``None``

Package configuration to load. Documentation generated under a configuration
describes the project *as that configuration leaves it*, which is usually what
you want when the configuration is what your readers use.

``dvflow_internal``
===================

:Type: ``bool``
:Default: ``False``

Include package-internal tasks — those declaring no scope — in
``dvf:autopackage``.

Off by default because visibility is already the audience model: a task with no
scope is not part of the package's published surface. Turning this on is
reasonable for a document aimed at the project's own maintainers.

It never includes ``local`` tasks. Those are fragment-scoped, so a reader cannot
address one whatever the documentation says.

``dvflow_show_source``
======================

:Type: ``bool``
:Default: ``True``

Show the ``Defined in flow.yaml:NN`` line at the end of each task.

Rebuild behavior
================

All four are registered with ``rebuild='env'``: changing any of them changes
*what gets extracted*, so the parsed environment is invalidated. A setting that
rebuilt only the output would leave a stale page that nothing but ``-E`` fixes,
with no indication of why.

Flow files are registered as build dependencies, so editing one rebuilds the
pages that document it. Without that, an incremental build would leave generated
pages stale — the ``.rst`` did not change, so Sphinx would have no reason to
think the page had.

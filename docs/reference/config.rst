#############
Configuration
#############

All settings are optional. The common case — one flow project, documented from a
``docs/`` directory inside it — needs no configuration at all.

What to document
================

``dvflow_root``
---------------

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
-----------------

:Type: ``str`` or ``None``
:Default: ``None``

Package configuration to load. Documentation generated under a configuration
describes the project *as that configuration leaves it*, which is usually what
you want when the configuration is what your readers use.

``dvflow_internal``
-------------------

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
----------------------

:Type: ``bool``
:Default: ``True``

Show the ``Defined in flow.yaml:NN`` line at the end of each object.

``dvflow_doc_format``
---------------------

:Type: ``str``
:Default: ``'rst'``

How ``doc:`` prose is interpreted: ``'rst'``, ``'markdown'`` or ``'plain'``.

``doc:`` is not read only by Sphinx. The same string reaches ``dfm show``,
``dfm llms``, and editor hovers — none of which render reStructuredText — so
flow-file prose is very often written in Markdown. ``'rst'`` is the default
because it is what a project documenting itself with Sphinx will write.

``'markdown'`` uses ``myst_parser`` when it is installed. Without it, a
deliberately small conversion handles the two constructs that make otherwise
valid prose fail to parse as reStructuredText — fenced code blocks and
single-backtick code spans. Everything else (``**bold**``, ``*emphasis*``,
bullet lists, block quotes) already means the same thing in both, which is what
makes a conversion that small worth having.

Whatever the format, **prose that fails to parse falls back to ``'plain'``**
rather than emitting docutils system messages onto the page. A sentence someone
wrote is worth showing even when its markup is wrong.

Diagrams
========

``dvflow_diagram_backend``
--------------------------

:Type: ``str``
:Default: ``'mermaid'``

Either ``'mermaid'`` or ``'graphviz'``. Mermaid is the default because it needs
no binary on the machine building the documentation; Graphviz produces better
layouts for large graphs and requires ``dot``.

Both are loaded by this extension rather than by your ``conf.py``. Whichever you
pick, every diagram has a textual twin, so a builder that renders neither (such
as ``text`` or ``man``) still carries the same facts.

``dvflow_diagram_depth``
------------------------

:Type: ``int``
:Default: ``1``

How many levels of nested compound task to expand in a sub-flow diagram. Deeper
diagrams are rarely more informative: past the first level the reader is looking
at a task that has its own page.

``dvflow_diagram_max_nodes``
----------------------------

:Type: ``int``
:Default: ``40``

Above this, a diagram is truncated and says so on the page. A picture with two
hundred boxes is not a picture — but silently dropping half of one is worse, so
the truncation is always stated.

``dvflow_diagram_dataflow``
---------------------------

:Type: ``bool``
:Default: ``True``

Draw inferred producer→consumer edges alongside the declared ``needs:`` edges.
An inferred edge is useful and is still an inference; turn this off for a
diagram containing only what the author wrote.

``dvflow_elaborate``
--------------------

:Type: ``bool``
:Default: ``False``

Allow the ``dvf:elaborated`` directive to expand a task through the engine. Off
by default because an elaborated graph is one machine's expansion of one
configuration: a different ``-D``, a different environment, a different picture.

Examples
========

See :doc:`../guide/examples`.

``dvflow_examples_dir``
-----------------------

:Type: ``str``
:Default: ``'examples'``

Directory holding adjacent example files, relative to the documentation source
directory. ``examples/<task>.rst`` is included on that task's page.

The directory is added to ``exclude_patterns`` automatically. Without that,
Sphinx would build each example as a page of its own and warn that it is in no
toctree — failing a ``-W`` build for doing exactly what the convention asks.

Set it to ``''`` to switch adjacent files off entirely.

``dvflow_examples_generate``
----------------------------

:Type: ``bool``
:Default: ``True``

Synthesize a minimal snippet for a task with no authored example. Always
labelled ``(generated)``: it is a synthesis of the declaration, not something
anyone asserted works.

``dvflow_examples_validate``
----------------------------

:Type: ``bool``
:Default: ``True``

Load every flow-fragment example during the build. A broken example warns —
which fails the build under ``-W`` — and says so on the page next to the code.

``dvflow_examples_diagrams``
----------------------------

:Type: ``bool``
:Default: ``False``

Draw the flow that a validated example declares. Off by default because it
costs a second load per example.

Cross-project links
===================

See :doc:`cross_project`.

``dvflow_intersphinx_packages``
-------------------------------

:Type: ``list[str]``
:Default: ``[]``

Flow packages that another project documents. A reference to one of them does
not warn when it does not resolve locally, and the auto directives decline to
document it.

Names, not URLs — the URL half is ``intersphinx_mapping``, which already knows
how to fetch an inventory.

``dvflow_schema_url``
---------------------

:Type: ``str``
:Default: ``''``

Where the flow-file schema reference is published. Either a template containing
``{key}`` or a base URL, in which case the key becomes the anchor. When set,
structural keys on a rendered page link to their schema entry.

Empty by default because there is no correct default: the spec lives wherever a
given project publishes it, and a guessed URL is a broken link on every page.

Coverage
========

See :doc:`../guide/coverage`.

``dvflow_coverage``
-------------------

:Type: ``bool``
:Default: ``False``

Write a documentation-coverage report at the end of the build, as
``dvflow-coverage.txt`` next to the built pages, plus a summary line in the
build log.

``dvflow_coverage_warn``
------------------------

:Type: ``bool``
:Default: ``False``

Turn every coverage finding into a warning. Off by default: an undocumented
task is a finding, not a broken build, and making it a warning fails every
``-W`` build over a missing sentence — after which the usual response is to
switch the report off and lose all of it.

Rebuild behavior
================

Every setting that changes *what gets extracted* is registered with
``rebuild='env'``, so changing one invalidates the parsed environment. A setting
that rebuilt only the output would leave a stale page that nothing but ``-E``
fixes, with no indication of why.

The two coverage settings are the exception. They report on what was extracted
rather than changing it, so asking for a report does not re-read every document.

Flow files are registered as build dependencies, so editing one rebuilds the
pages that document it. Without that, an incremental build would leave generated
pages stale — the ``.rst`` did not change, so Sphinx would have no reason to
think the page had. Adjacent example files are registered the same way.

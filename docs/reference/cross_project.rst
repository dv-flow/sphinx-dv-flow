##############################
Cross-Project and Schema Links
##############################

Two settings, one idea: a name on a page should reach whatever documents it,
even when that is not this documentation set.

Linking to another flow library
===============================

The ``dvf`` domain writes ``objects.inv`` entries for every object type, so any
Sphinx project can ``intersphinx`` to a flow library:

.. code-block:: python

    extensions = ["sphinx.ext.intersphinx", "sphinx_dv_flow"]
    intersphinx_mapping = {
        "hdl": ("https://example.org/hdl-lib/", None),
    }

A ``:dvf:task:`hdl.sim.image``` then resolves against that project's inventory
and becomes a link.

``dvflow_intersphinx_packages``
===============================

Sphinx can be told where another project's documentation lives. What it cannot
know is *which flow packages* are somebody else's to document:

.. code-block:: python

    dvflow_intersphinx_packages = ["std"]

That declaration does two things.

**References to those packages stop warning when unresolved.** A project
building on a library produces references to that library's tasks and types
constantly — from every ``produces:`` entry, every ``uses:`` chain — and under
``nitpicky`` each one is reported as a broken reference. The alternative most
projects reach for is:

.. code-block:: python

    nitpick_ignore_regex = [(r'dvf:.*', r'std\..*')]

which says "stop telling me about anything matching this pattern". Naming the
package instead says "another project documents this", which is narrower, and
which is *checked*: point ``intersphinx_mapping`` at that project and the same
references become links with no further change. A dangling reference to anything
in your own project still fails the build.

**The auto directives decline to document those packages.** Two documentation
sets describing the same object is worse than one: references resolve to
whichever inventory answers first, and the two copies drift independently. The
name still links, so declining to render it costs the reader nothing.

Ordering
--------

The warning for an unresolved reference is emitted from Sphinx's
``warn-missing-reference`` event, not from the domain's ``resolve_xref``. That
ordering is load-bearing: the reference resolver emits ``missing-reference``
first, which is where intersphinx resolves a name against another project's
inventory. Warning from ``resolve_xref`` fires before intersphinx has been asked
and reports every legitimate cross-project link as a broken one.

``dvflow_schema_url``
=====================

A rendered page says what a task declares; the flow-file schema says what a
declaration may contain. Those are two halves of one question, and readers fall
through the seam between them.

.. code-block:: python

    dvflow_schema_url = "https://dv-flow.github.io/spec.html#taskdef-{key}"

Structural keys on a rendered page — ``consumes:``, ``produces:``, ``with:``,
``needs:``, ``requires:``, ``strategy:``, and every key in the behavior table —
then link to their schema entry.

A base URL works too, in which case the key becomes the anchor:

.. code-block:: python

    dvflow_schema_url = "https://dv-flow.github.io/spec.html"

The link is **generated from the key name**. That is the whole design: a field
added to the schema upstream is linkable without touching this extension, and
there is no list here to fall out of date.

Off unless set, because there is no correct default — the spec lives wherever a
given project publishes it, and a guessed URL is a broken link on every page.

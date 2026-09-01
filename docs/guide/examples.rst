########
Examples
########

Extracted documentation is accurate but never sufficient. Nobody learns a task
from its parameter table — they learn it from something they can copy.

Three sources
=============

Authored in the flow file
-------------------------

An ``examples:`` entry on the task. Preferred, because the example lives next to
what it documents and moves with it:

.. code-block:: yaml

    tasks:
    - name: Compile
      examples:
      - title: From the command line
        lang: shell
        code: dfm run examples.Compile
      - title: In a flow
        caption: A complete fragment, so the docs build loads it.
        code: |
          fragment:
            tasks:
            - name: my-build
              uses: examples.Compile

Examples are deliberately **not** inherited along ``uses:``. An example is
written against a specific task name and a specific set of parameters, so
re-presenting a base task's example under a derived task would show the reader
something they cannot type.

An adjacent file
----------------

``examples/<task>.rst`` in the documentation source directory, included in place
on that task's page. The qualified name is tried first, then the leaf, so
``examples/Compile.rst`` works for a doc set covering one package and
``examples/library.Compile.rst`` disambiguates one covering several.

Included rather than linked: an example a reader has to click through to is an
example most readers will not read.

Generated
---------

Where nothing was authored, a minimal snippet synthesized from the declaration —
a command line for a runnable task, a ``uses:`` stanza otherwise. It fills in the
parameters that have no default, which is as close as the model gets to "the
ones you have to set".

Always labelled ``(generated)``. A reader who cannot tell a synthesized example
from an asserted one will trust both equally, and only one of them has been
looked at by a person.

Precedence
==========

Authored examples and an adjacent file are **both** shown. Both are deliberate
acts by a person, and suppressing a hand-written example page because someone
added a one-line ``examples:`` entry to the flow file would delete content
silently.

The generated snippet yields to either. It exists to fill an empty section, so
producing one beside a real example would be noise.

Validated examples
==================

An example that no longer parses is worse than no example: it is
indistinguishable from one that works until somebody types it, and documentation
examples rot quietly.

The engine is already loaded during a documentation build, so an example that is
a complete flow fragment is **loaded** — the ``dfm validate`` path. A broken one:

- warns, with the location of the flow file that declares it, which fails the
  build under ``-W``;
- says so on the page, next to the code, where someone about to copy it will
  see it.

Nothing is *run*. An example is documentation, and a documentation build that
executes a simulator has stopped being a documentation build.

Only fragments are checked. A shell command line or an excerpt is left unchecked
rather than wrapped in a synthesized package — there is no honest way to guess
the file around an excerpt, and validating a guess would report on something the
author never wrote. "Not checked" and "checked and fine" are different claims,
and the page makes neither where only the first is true.

Only failure is reported. A green badge on every working snippet is noise
proportional to the size of the doc set; the value of validation is that a
broken example stops being invisible.

Example diagrams
================

With ``dvflow_examples_diagrams``, a validated flow example is drawn as well as
shown. The picture is provably a picture of the code above it — which is the
whole argument for generating one rather than accepting a hand-drawn
approximation that drifted two releases ago.

Off by default: it costs a second load per example.

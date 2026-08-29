#########
Lifecycle
#########

A lifecycle tag is a claim about **interface churn**, not about runtime
behavior. A deprecated task still runs; deprecation is a message to whoever
reads or maintains the flow file.

Declaring it
============

.. code-block:: yaml

    tasks:
    - name: build-legacy
      uses: hdl.Compile
      tags:
      - std.Deprecated:
          reason: superseded by the incremental compile flow
          replacement: proj.build
          since: "1.4"

    - name: sim-vlt
      tags:
      - std.Experimental:
          reason: parameter names likely to change

    - name: sim-vcs
      tags:
      - std.Stable:
          since: "1.0"

What the rendering does with it
===============================

**Deprecated** gets a warning banner *before* the description, with
``replacement`` rendered as a link. Someone skimming to decide whether to depend
on a task will not reach a note at the bottom, and the most useful thing the
page can do for them is tell them not to before they read the parameters.

**Experimental** gets a note. It says "this may change", not "do not use" — the
point of the tag is to let you ship something useful before its interface has
settled.

**Stable** gets a badge and no banner. It is the assumed state, so an
admonition saying so on every page that declared it would compete with the
banners that carry an actual warning.

**Untagged** gets nothing. Absence is not a claim: a task that never said
anything is assumed stable, and giving every untagged task a badge would make
the badge meaningless.

Deprecated tasks and listings
=============================

``dvf:autopackage`` excludes deprecated tasks. A listing is a menu — it answers
"what can I use here", and a task nobody should use any more is a wrong answer.

The page still exists when asked for by name, so links from old flow files keep
working, and whoever follows one still gets the banner telling them what to move
to. To include them in a listing anyway:

.. code-block:: rst

    .. dvf:autopackage::
       :deprecated:

Saying there is no replacement
==============================

Leave ``replacement`` empty and the banner says *There is no replacement*. That
is deliberate: "use X instead" and "there is nothing to move to" lead a reader
to opposite decisions, so an empty replacement is treated as the statement it is
rather than as a missing field.

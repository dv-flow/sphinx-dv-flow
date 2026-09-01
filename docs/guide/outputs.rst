###################
Documenting Outputs
###################

A task produces zero or more outputs. There are two levels of describing them,
and they answer different questions.

By kind
=======

``produces:`` declares the item **type**, which is the minimum:

.. code-block:: yaml

    tasks:
    - name: gen-ral
      produces:
      - type: std.FileSet
        filetype: verilogSource

That is what the engine needs. It is what lets a consumer declare
``consumes: [{type: std.FileSet, filetype: verilogSource}]`` and have the two
wire up, and it is what the dataflow check verifies.

It is not what a *person* needs. "An ``std.FileSet`` of Verilog source" does not
tell anyone that the file lands at ``ral_pkg.sv`` in the run directory.

By documentation
================

Add ``doc:`` to the entry:

.. code-block:: yaml

    tasks:
    - name: gen-ral
      produces:
      - type: std.FileSet
        filetype: verilogSource
        doc: ${{ task_rundir }}/ral_pkg.sv

which renders as:

.. code-block:: text

    Produces (may produce)
      std.FileSet filetype=verilogSource — ${{ task_rundir }}/ral_pkg.sv

Two properties
==============

**It is not an attribute.** Every other key in a ``produces:`` entry is
something a consumer can match on. ``doc:`` is excluded from matching, so a
producer's wording is never part of the wiring — editing a sentence cannot
change which tasks connect to which.

**It is not evaluated.** ``${{ task_rundir }}`` reaches the page as written.
Resolving it would bake whichever machine built the documentation into the page,
and outside a run there is nothing for it to resolve to. The *shape* of the path
is what documents the output; one resolution of it is not.

That second property is the reason this is prose rather than a declared file
list. What generalises across every run of the task is the pattern, and the
pattern is exactly what an author can write down accurately.

What this deliberately is not
=============================

There is no schema for outputs: no declared filenames, no globs, no
copied-out-of-the-run-directory manifest. Those are all attempts to describe
something the task itself decides at run time, and every one of them is either a
duplicate of the task's implementation or a claim that quietly stops being true.

Nor is anything **discovered** by running the task and looking at what appeared.
A documented output is one the author committed to; a scanned one is whatever
happened on the machine that scanned it, which is a different — and much weaker
— statement. This follows the same rule as everywhere else in the extension:
declared over discovered.

If a task's outputs genuinely need more structure than a sentence, that is worth
knowing about with a concrete case in hand, rather than guessed at now.

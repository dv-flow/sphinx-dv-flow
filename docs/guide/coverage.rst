########
Coverage
########

A generated documentation set hides missing documentation particularly well.
Every public task gets a heading and a parameter table whether or not anyone
described it, so the output looks complete at exactly the density where it is
emptiest.

The coverage report makes that visible.

From the command line
=====================

.. code-block:: shell

    dvflow-doc coverage -r path/to/project

.. code-block:: text

    Documentation coverage: 5/8 documented (62%), 3 missing

    task coverage.Bare  (flow.yaml:41)
        no desc: or doc:

    task coverage.PartlyBare  (flow.yaml:45)
        parameter 'bare' has no desc: or doc:

    type coverage.Undescribed  (flow.yaml:28)
        no desc: or doc:

``--strict`` exits non-zero when anything is undocumented, so a CI job can gate
on it. ``--json`` emits the same report as data.

During a build
==============

Set ``dvflow_coverage = True`` and the build writes ``dvflow-coverage.txt`` next
to the built pages and logs a summary line. It reports over what the build
actually loaded, because "what did I publish undocumented" is the question, and
a package the doc set never mentions cannot answer it.

``dvflow_coverage_warn`` turns each finding into a warning. It is off by default
and deliberately: an undocumented task is a finding, not a broken build. Making
it a warning fails every ``-W`` build over a missing sentence, and the usual
response to that is to switch the report off — losing all of it.

What counts
===========

Coverage is measured over the **published** surface. Something a reader cannot
address is not a gap:

- ``local`` tasks and filters are never counted. They are fragment-scoped, so
  nobody outside can name them.
- Package-internal objects are counted only with ``--internal``, matching what
  the documentation actually publishes.
- A parameter is charged to the task that **introduced** it, not to every task
  that inherits it. Charging inheritors would report one missing sentence N
  times and turn the count into a measure of inheritance depth.

Either ``desc:`` or ``doc:`` is enough. A one-liner is a real answer to "what is
this", and demanding both would make the report a style check — which is how a
report stops being read.

The denominator is part of the report. "Three findings" says nothing on its own,
and a report that counts only failures cannot show progress.

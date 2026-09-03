##############
sphinx-dv-flow
##############

Sphinx support for documenting `DV Flow <https://github.com/dv-flow/dv-flow-mgr>`_
workflows.

A flow file already states what a task takes, what it produces and how it is
reached. ``sphinx-dv-flow`` reads those statements and renders them, so the
documentation says what the flow actually does rather than what it did when
someone last updated a table by hand.

The project has two halves, and the split matters:

``dv_flow.doc``
    Loads a project and extracts documentation facts as plain data. It does not
    import Sphinx, and a test enforces that. This is what makes the extracted
    model testable on its own, and reusable by tools that have no business
    depending on a documentation generator.

``sphinx_dv_flow``
    The Sphinx extension. Directives, roles, indices and diagrams -- rendering
    only.

.. note::

   Early development. The extraction and rendering layers, the ``dvf`` domain,
   diagrams, examples, coverage reporting and cross-project references are in
   place, and ``dv-flow-mgr`` generates its own standard-library reference with
   this extension. The directive and configuration surface is not frozen --
   hence ``0.0.x``. See ``PLAN.md`` in the repository root for what is still
   outstanding.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   install
   quickstart
   guide/index
   example
   reference/index

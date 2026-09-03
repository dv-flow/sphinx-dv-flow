############
Installation
############

From PyPI
=========

.. code-block:: shell

    pip install sphinx-dv-flow

That pulls in ``dv-flow-mgr`` and ``sphinx``. The extension reads a flow project
through the engine's own loader rather than parsing YAML itself, which is why
the engine is a hard dependency and not an optional one -- see
:doc:`reference/extraction`.

From source
===========

.. code-block:: shell

    pip install -e .

Extras
------

``[graphviz]``
    Graphviz rendering backend for diagrams. Without it, diagrams render as
    Mermaid, which needs no external tool.

``[markdown]``
    ``myst-parser``, which makes ``dvflow_doc_format = "markdown"`` handle
    general Markdown. Without it, ``doc:`` prose written in Markdown still
    renders -- a deliberately small conversion covers fenced code blocks and
    single-backtick code spans, the two constructs that make otherwise-fine
    prose fail to parse as reStructuredText. So this is an upgrade, not a
    requirement.

``[test]``
    ``pytest``, for running the test suite.

``[docs]``
    ``furo`` and ``sphinxcontrib-mermaid``, for building these docs.

Enabling the extension
======================

Add it to ``extensions`` in your ``conf.py``:

.. code-block:: python

    extensions = [
        "sphinx_dv_flow",
    ]

Development setup
=================

The repository uses `ivpm <https://github.com/fvutils/ivpm>`_ to assemble a
development environment, including a checkout of ``dv-flow-mgr``:

.. code-block:: shell

    ivpm update -a

That creates a virtual environment at ``packages/python`` with everything the
tests and the docs build need.

.. code-block:: shell

    ./packages/python/bin/pytest
    ./packages/python/bin/sphinx-build -W -b html docs docs/_build/html

The docs build runs with ``-W`` in CI. These docs are the acceptance test for
the directives the extension ships, so a warning here is a failure.

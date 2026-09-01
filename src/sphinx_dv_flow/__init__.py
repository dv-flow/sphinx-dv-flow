"""Sphinx extension that renders DV Flow documentation.

Everything here is rendering. The facts come from :mod:`dv_flow.doc`, which
does not import Sphinx; this package turns those facts into docutils nodes.
Keeping the dependency one-directional is what lets the extraction contract be
tested as data and reused by ``dfm`` (see :mod:`dv_flow.doc`).

Enable it with::

    extensions = ["sphinx_dv_flow"]
"""

__all__ = [
    "setup",
    "__version__",
]

from dv_flow.doc import __version__


def setup(app):
    """Sphinx entry point."""
    from .config import exclude_examples, setup_config
    from .directives.auto import DvfAutoPackage, DvfAutoTask, DvfAutoType
    from .directives.diagrams import (DvfDataflow, DvfElaborated,
                                      DvfFlowDiagram, DvfInheritance,
                                      DvfPackageDiagram)
    from .directives.package_objects import DvfAutoConfig, DvfAutoFilter
    from .domain import DvfDomain, warn_missing_reference
    from .env import purge
    from .indices import ALL_INDICES
    from .coverage import report as coverage_report
    from .render.diagrams import resolve_diagrams

    setup_config(app)
    # Before Sphinx enumerates source files: the examples directory is included
    # into task pages, not built as pages of its own.
    app.connect('config-inited', exclude_examples)

    # Diagrams are emitted as `mermaid` or `graphviz` nodes, so the extensions
    # that know how to write them have to be loaded -- by us, not by the user's
    # `conf.py`. A doc set that enables `sphinx_dv_flow` and gets an "unknown
    # node type" crash the first time it documents a compound task has been
    # handed a dependency it was never told about.
    #
    # `sphinx.ext.graphviz` registers the node type without needing the `dot`
    # binary; that is only required when a graphviz-backed diagram is actually
    # rendered, which is why graphviz is not the default backend.
    #
    # Not fatal when a package is absent: `render/diagrams.py` falls back to a
    # plain literal block carrying the same diagram source, which is readable
    # and complete.
    for extension in ('sphinxcontrib.mermaid', 'sphinx.ext.graphviz'):
        try:
            app.setup_extension(extension)
        except Exception:
            pass

    # Loaded projects are cached per build, outside the environment -- see
    # `env.py` for why they must not be stored on it.
    app.connect('builder-inited', purge)

    app.add_domain(DvfDomain)
    # After intersphinx, not before it: a reference to another project's flow
    # package is a link, not a defect, and warning from `resolve_xref` reports
    # it as one.
    app.connect('warn-missing-reference', warn_missing_reference)
    for index in ALL_INDICES:
        app.add_index_to_domain('dvf', index)
    app.add_directive_to_domain('dvf', 'autotask', DvfAutoTask)
    app.add_directive_to_domain('dvf', 'autotype', DvfAutoType)
    app.add_directive_to_domain('dvf', 'autopackage', DvfAutoPackage)
    app.add_directive_to_domain('dvf', 'autoconfig', DvfAutoConfig)
    app.add_directive_to_domain('dvf', 'autofilter', DvfAutoFilter)
    app.add_directive_to_domain('dvf', 'flowdiagram', DvfFlowDiagram)
    app.add_directive_to_domain('dvf', 'inheritance', DvfInheritance)
    app.add_directive_to_domain('dvf', 'dataflow', DvfDataflow)
    app.add_directive_to_domain('dvf', 'packagediagram', DvfPackageDiagram)
    app.add_directive_to_domain('dvf', 'elaborated', DvfElaborated)

    # Diagram links are filled in at `doctree-resolved`, not when the directive
    # runs: the domain inventory is still filling during the read phase, so
    # baking URLs in early would silently drop every forward link -- and would
    # do it differently depending on document order.
    app.connect('doctree-resolved', resolve_diagrams)

    # Reported at the end, over what the build actually loaded. Off unless
    # `dvflow_coverage` is set -- see `coverage.py` for why it is neither on by
    # default nor a warning.
    app.connect('build-finished', coverage_report)

    return {
        "version": __version__,
        # Safe because `DvfDomain.merge_domaindata` exists: each parallel
        # worker builds its own object inventory, and without a merge the
        # objects described in a subprocess-read document would be lost --
        # dangling every reference to them, intermittently, depending on how
        # work happened to be distributed.
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

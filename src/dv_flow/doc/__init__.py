"""Extraction of documentation facts from a DV Flow project.

This package answers questions about a flow -- what tasks exist, what
parameters they take, what they produce -- and returns plain data. It knows
nothing about Sphinx, reStructuredText, or HTML.

That separation is the one structurally expensive decision in this project, so
it is enforced by a test rather than by intent: importing anything under
``dv_flow.doc`` must leave ``sphinx`` absent from ``sys.modules``. Two things
depend on it. ``dfm`` may eventually consume the extractor (for ``dfm llms``,
or for documentation-linked error messages) and must not acquire a Sphinx
dependency by doing so; and the extraction contract stays testable as data,
without standing up a Sphinx build to look at it.

The rendering layer lives in :mod:`sphinx_dv_flow` and depends on this one.
Never the reverse.
"""

__all__ = [
    "__version__",
]

try:
    from importlib.metadata import PackageNotFoundError, version as _version
    try:
        __version__ = _version("sphinx-dv-flow")
    except PackageNotFoundError:  # running from a source tree, not installed
        __version__ = "0.0.0.dev0"
except ImportError:  # pragma: no cover - Python <3.8
    __version__ = "0.0.0.dev0"

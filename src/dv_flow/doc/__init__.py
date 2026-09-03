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

# From the source file rather than from installed metadata: the tests, the
# consistency layer and `dvflow-doc --version` all run against a checkout that
# was never `pip install`ed, where `importlib.metadata` reports either a stale
# version from a previous install or nothing at all. See `__version__.py`.
from .__version__ import __version__

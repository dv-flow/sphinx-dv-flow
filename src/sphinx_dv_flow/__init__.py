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
    """Sphinx entry point.

    M0 registers nothing: the config values, the ``dvf`` domain, the
    directives and the indices arrive with the milestones that define them.
    The hook exists now so that ``extensions = ["sphinx_dv_flow"]`` is a valid
    thing to write from the first commit, and so the docs build in CI exercises
    the real load path rather than a stub added later.
    """
    return {
        "version": __version__,
        # The extension holds no cross-document state yet. Both are revisited
        # when the `dvf` domain lands in M2 -- a domain's inventory has to be
        # merged for parallel reads to be safe, and claiming safety before
        # that code exists is how silent cross-reference loss happens.
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

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
    from .config import setup_config
    from .directives.auto import DvfAutoPackage, DvfAutoTask, DvfAutoType
    from .domain import DvfDomain
    from .env import purge

    setup_config(app)

    # Loaded projects are cached per build, outside the environment -- see
    # `env.py` for why they must not be stored on it.
    app.connect('builder-inited', purge)

    app.add_domain(DvfDomain)
    app.add_directive_to_domain('dvf', 'autotask', DvfAutoTask)
    app.add_directive_to_domain('dvf', 'autotype', DvfAutoType)
    app.add_directive_to_domain('dvf', 'autopackage', DvfAutoPackage)

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

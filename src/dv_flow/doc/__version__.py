"""The package version, and the only place it is written down.

``VERSION`` is the released number and ``SUFFIX`` is empty in the source tree.
CI rewrites ``SUFFIX`` -- and nothing else -- so that a build off a branch
carries a unique, unpublishable development version without anyone hand-editing
a file.

**One copy, deliberately.** ``pyproject.toml`` declares ``dynamic = ["version"]``
and reads ``_pkg_version`` from this module, so the distribution metadata and
the runtime ``__version__`` cannot disagree. The alternative -- a literal in
``pyproject.toml`` *and* a literal in Python, both rewritten by ``sed`` at build
time -- is the arrangement that lets a package report one version to ``pip`` and
another to ``import``, silently, because ``sed`` does not fail when its pattern
matches nothing. There is nothing here for it to get out of step with.

This module must stay importable on its own: the build backend reads
``_pkg_version`` from it before the package's dependencies (``dv_flow.mgr``,
``sphinx``) exist. Import nothing.
"""

VERSION = "0.0.1"
SUFFIX = ""

__version__ = VERSION + SUFFIX

#: Read by ``pyproject.toml``'s ``[tool.setuptools.dynamic]`` version hook.
_pkg_version = __version__

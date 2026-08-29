"""Loading a DV Flow project, with its diagnostics kept rather than raised.

Two things distinguish this from calling `loadProjPkgDef` directly.

**Markers are collected, not printed.** The engine reports parse problems as
`TaskMarker`s carrying a source location. A docs build needs those as warnings
with a `flow.yaml:line`, not as a traceback and not on stdout, so the listener
hands them back to the caller to route (design §7).

**A failed load returns a result, not an exception.** The caller -- a Sphinx
directive -- has to emit a located warning and carry on with the rest of the
document. Raising through a directive turns one bad flow file into a build with
no output at all.

Caching lives with the caller (the Sphinx build environment, keyed by root path
and config), not here: this module has no way to know when a file changed, and
a cache that cannot be invalidated is a bug waiting for someone to edit a flow
file and not see it.
"""

import dataclasses as dc
import os
from typing import Any, Dict, List, Optional


@dc.dataclass
class Marker:
    """A diagnostic from the loader, flattened away from engine types.

    Flattened deliberately: this is the shape a renderer forwards to
    `logger.warning(..., location=...)`, and keeping the engine's pydantic model
    out of the contract is what lets the extraction document stay plain data.
    """
    msg: str = ""
    severity: str = "error"
    file: Optional[str] = None
    line: int = -1

    @property
    def is_error(self) -> bool:
        return self.severity == "error"

    def location(self) -> Optional[str]:
        """`file:line`, or None when the marker has no source location."""
        if not self.file:
            return None
        return "%s:%d" % (self.file, self.line) if self.line > 0 else self.file


@dc.dataclass
class LoadResult:
    """What a load produced, including when it produced nothing.

    `pkg is None` means the project did not load. `markers` says why, with a
    location -- so the caller can report it against the flow file rather than
    against the document that happened to reference it.
    """
    pkg: Any = None
    loader: Any = None
    root: str = ""
    markers: List[Marker] = dc.field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.pkg is not None

    @property
    def errors(self) -> List[Marker]:
        return [m for m in self.markers if m.is_error]

    def flow_files(self) -> List[str]:
        """Every flow file that contributed, for `env.note_dependency()`.

        Incremental builds are the reason this exists: without it, editing a
        flow file leaves the generated page stale and there is nothing to
        suggest why.
        """
        files = []
        seen = set()

        def _add(path):
            if path and path not in seen:
                seen.add(path)
                files.append(path)

        pkg = self.pkg
        if pkg is None:
            return files

        for holder in (getattr(pkg, 'task_m', {}) or {},
                       getattr(pkg, 'type_m', {}) or {}):
            for obj in holder.values():
                srcinfo = getattr(obj, 'srcinfo', None)
                _add(getattr(srcinfo, 'file', None))

        # The package's own file, which has no task to carry it if the package
        # declares none.
        pkg_srcinfo = getattr(getattr(pkg, 'pkg_def', None), 'srcinfo', None)
        _add(getattr(pkg_srcinfo, 'file', None))

        return files


def _to_marker(m) -> Marker:
    severity = getattr(m, 'severity', None)
    loc = getattr(m, 'loc', None)
    return Marker(
        msg=getattr(m, 'msg', str(m)),
        severity=str(getattr(severity, 'value', severity) or 'error').lower(),
        file=getattr(loc, 'path', None) if loc is not None else None,
        line=getattr(loc, 'line', -1) if loc is not None else -1)


def load_project(path: str,
                 config: Optional[str] = None,
                 parameter_overrides: Optional[Dict[str, Any]] = None
                 ) -> LoadResult:
    """Load the project rooted at `path`.

    `path` may be a directory (the flow file is searched for, upward, as `dfm`
    does) or a flow file directly.

    An exception from the engine is converted into an error marker rather than
    propagated. That is not defensiveness for its own sake: ground rule §0.4
    says a docs build may fail on a malformed flow file, but it must fail with a
    location, and only the caller knows how to report one.
    """
    from dv_flow.mgr.util import loadProjPkgDef

    markers: List[Marker] = []
    root = os.path.abspath(path)

    def _listener(m):
        markers.append(_to_marker(m))

    loader = None
    pkg = None
    try:
        loader, pkg = loadProjPkgDef(
            root,
            listener=_listener,
            parameter_overrides=parameter_overrides,
            config=config)
    except Exception as e:
        markers.append(Marker(
            msg="failed to load flow project: %s: %s" % (type(e).__name__, e),
            severity="error",
            file=root if os.path.isfile(root) else None))

    if pkg is None and not markers:
        # A silent failure is the one case a caller cannot report usefully, so
        # it gets a marker of its own rather than an empty result.
        markers.append(Marker(
            msg="no flow package found at %s" % root,
            severity="error"))

    return LoadResult(pkg=pkg, loader=loader, root=root, markers=markers)


def iter_tasks(pkg):
    """Tasks of `pkg`, in declaration order where the engine preserves it.

    `task_m` is insertion-ordered by the loader, so this follows the flow file
    rather than imposing an alphabetical order the author did not choose.
    """
    return list((getattr(pkg, 'task_m', {}) or {}).values())


def iter_types(pkg):
    return list((getattr(pkg, 'type_m', {}) or {}).values())


def find_task(pkg, name: str):
    """Resolve `name` against `pkg`, accepting the unqualified leaf form.

    A document that says `dvf:autotask:: run` inside a package's own docs
    should not have to repeat the package name. Fully-qualified is tried first
    so an exact name can never be shadowed by a leaf match.
    """
    task_m = getattr(pkg, 'task_m', {}) or {}
    if name in task_m:
        return task_m[name]

    qualified = "%s.%s" % (getattr(pkg, 'name', ''), name)
    if qualified in task_m:
        return task_m[qualified]

    matches = [t for n, t in task_m.items() if n.split('.')[-1] == name]
    return matches[0] if len(matches) == 1 else None

"""Filter extraction (design §4.7).

A filter is invoked, never run on its own: it appears on the right of a `|` in
an expression, so the thing being documented is a call. Extraction therefore
builds the signature -- what the reader types -- rather than leaving each
renderer to compose it from parts and get it subtly different.

**Filters are declared but not yet resolved by the engine** (PLAN.md U14): a
`Package` carries no `filters`, so the registration in `TaskGraphBuilder` never
fires, and no `ExprEval` is given a registry. The declarations are real and
worth documenting -- they are what the author committed to -- but a page that
presented them as usable today would be telling a reader to type something that
fails. `ACTIVE` records that, in one place, so the day it changes is a one-line
change here rather than an audit of every renderer.
"""

from typing import List, Optional

from .model import FilterDoc, ParamDoc, SrcRef

# Whether the engine resolves package-declared filters in expressions. False
# until U14 lands upstream; renderers consult it to decide whether to caveat.
ACTIVE = False


def _srcref(obj) -> Optional[SrcRef]:
    srcinfo = getattr(obj, 'srcinfo', None)
    if srcinfo is None:
        return None
    file = getattr(srcinfo, 'file', None)
    if not file:
        return None
    return SrcRef(file=file, line=getattr(srcinfo, 'lineno', None)
                  or getattr(srcinfo, 'line', 0) or 0)


def _scope_of(fd) -> List[str]:
    """Declared visibility, as a list so it reads like a task's scope.

    A filter's visibility is spelled the same way a task's is (`export:`,
    `local:`, `root:` in place of `name:`), and it means the same thing, so it
    is extracted into the same shape rather than into a filter-specific one.
    """
    scope = getattr(fd, 'scope', None)
    if scope is None:
        return []
    if isinstance(scope, str):
        return [scope]
    return list(scope)


def is_local(fd) -> bool:
    return 'local' in _scope_of(fd)


def is_documented_by_default(fd) -> bool:
    """The same audience model as tasks (design §3), read off the same words.

    `export` and `root` are declarations that someone outside is meant to use
    them, so they are documented. An unscoped filter is visible only within its
    own package -- package-internal, exactly like an unscoped task -- so it
    appears only under `:internal:`. A `local` filter is fragment-scoped and
    never appears: a reader outside the fragment cannot name it, so documenting
    it would offer something that cannot be used.
    """
    scope = _scope_of(fd)
    return bool({'export', 'root'} & set(scope))


def _params(fd) -> List[ParamDoc]:
    """Filter arguments, in declaration order.

    Order is load-bearing here in a way it is not for a task: arguments bind
    positionally as `$arg0`, `$arg1`, so the sequence a filter was declared in
    is part of its interface. The mapping is preserved as declared and never
    sorted.
    """
    out = []
    params = getattr(fd, 'params', None) or {}
    items = params.items() if hasattr(params, 'items') else []
    for index, (name, pd) in enumerate(items):
        ptype = getattr(pd, 'type', None) or 'any'
        out.append(ParamDoc(
            name=name,
            type=str(ptype),
            default=getattr(pd, 'value', None),
            desc=getattr(pd, 'desc', '') or '',
            doc=getattr(pd, 'doc', '') or '',
            # The positional slot the argument fills. Carried in `define`
            # because that field already means "the other way to name this
            # parameter", which is exactly what `$arg0` is.
            define="$arg%d" % index,
        ))
    return out


def signature(fd) -> str:
    """The call, as written in an expression.

    `${{ inputs | name(a, b) }}` with the arguments named, or `${{ inputs |
    name }}` when there are none. `inputs` is a placeholder for whatever the
    left-hand side is; showing a concrete one would suggest the filter only
    applies there.
    """
    name = getattr(fd, 'name', '') or ''
    params = getattr(fd, 'params', None) or {}
    names = list(params.keys()) if hasattr(params, 'keys') else []
    call = "%s(%s)" % (name, ", ".join(names)) if names else name
    return "${{ inputs | %s }}" % call


def extract_filter(fd, pkg=None) -> FilterDoc:
    package = getattr(pkg, 'name', '') if pkg is not None else ''
    run = getattr(fd, 'run', None)
    return FilterDoc(
        name=getattr(fd, 'name', ''),
        package=package,
        desc=getattr(fd, 'desc', '') or '',
        doc=getattr(fd, 'doc', '') or '',
        srcinfo=_srcref(fd),
        scope=_scope_of(fd),
        params=_params(fd),
        impl='run' if run else 'expr',
        body=(run or getattr(fd, 'expr', '') or ''),
        shell=(getattr(fd, 'shell', '') or '') if run else '',
        signature=signature(fd),
    )


def iter_filters(pkg):
    """Every filter the package declares, from the package file and fragments.

    Fragments are included because organizing filters into one is the obvious
    thing to do -- `std` does exactly that -- and a package that did would
    otherwise document none of them.
    """
    seen = set()
    out = []

    pkg_def = getattr(pkg, 'pkg_def', None)
    sources = [pkg_def] + list(getattr(pkg, 'fragment_def_l', None) or [])
    for source in sources:
        for fd in (getattr(source, 'filters', None) or []):
            name = getattr(fd, 'name', None)
            # A redeclared name shadows rather than adds: the registry warns
            # and keeps one, so documenting both would show a reader a
            # definition that never runs.
            if name is None or name in seen:
                continue
            seen.add(name)
            out.append(fd)
    return out


def find_filter(pkg, name):
    for fd in iter_filters(pkg):
        if getattr(fd, 'name', None) == name:
            return fd
        if getattr(fd, 'name', None) == name.split('.')[-1]:
            return fd
    return None


def documented_filters(pkg, internal: bool = False) -> List:
    return [fd for fd in iter_filters(pkg)
            if not is_local(fd)
            and (is_documented_by_default(fd) or internal)]

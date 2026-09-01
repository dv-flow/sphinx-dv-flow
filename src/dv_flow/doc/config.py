"""Configuration extraction (design §4.7).

A configuration is a named way to load a package: select it and some tasks,
types, imports or fragments are different from what the default load produced.
That makes it the one documented object whose subject is *not on the page it
documents* -- the tasks a config overrides are documented as they load by
default, because that is the load the docs build performed.

So the contract here is names and locations, not expansions. Rendering a
config's overridden task in place would show the reader a task that the rest of
the doc set contradicts, with nothing to say which one they are looking at.
"""

from typing import List, Optional

from .model import ConfigDoc, SrcRef


def _srcref(obj) -> Optional[SrcRef]:
    srcinfo = getattr(obj, 'srcinfo', None)
    if srcinfo is None:
        return None
    file = getattr(srcinfo, 'file', None)
    if not file:
        return None
    return SrcRef(file=file, line=getattr(srcinfo, 'lineno', None)
                  or getattr(srcinfo, 'line', 0) or 0)


def iter_configs(pkg):
    """The configurations a package declares, in declaration order.

    `all_configs` rather than `pkg_def.configs`: a package may organize its
    configurations into fragments, and a reader selecting one with `-c` does
    not care which file it was written in. The engine unifies them for exactly
    that reason, so reading the unified list keeps documentation and selection
    speaking about the same set.
    """
    return list(getattr(pkg, 'all_configs', None) or [])


def find_config(pkg, name):
    for cfg in iter_configs(pkg):
        if getattr(cfg, 'name', None) == name:
            return cfg
    return None


def _target_names(entries, package=None) -> List[str]:
    """Names of the tasks or types an entry list redefines.

    A config entry names its target in `override:` when it replaces something
    and in `name:` when it adds something new. Both are "what this
    configuration changes" from the reader's side, so both are collected.

    Qualified with the package name, because that is how the target is
    documented and how it is referred to anywhere else. An unqualified `Build`
    is not merely terse: leaf matching resolves it only when it is unique
    across the whole doc set, so as soon as a second package has a `Build` the
    link silently stops working.
    """
    out = []
    for entry in entries or []:
        name = (getattr(entry, 'override', None)
                or getattr(entry, 'name', None))
        if not name:
            continue
        if package and '.' not in name:
            name = "%s.%s" % (package, name)
        out.append(name)
    return out


def _override_pairs(cfg) -> List[str]:
    """Package-level `overrides:` as "target -> replacement" strings.

    Flattened to strings because the replacement may be either a name or a
    whole inline task definition, and a reader needs to see *that it is
    inline* more than they need its body -- the body is the config's source,
    which the location points at.
    """
    out = []
    for entry in getattr(cfg, 'overrides', None) or []:
        target = (getattr(entry, 'target_task', None)
                  or getattr(entry, 'package', None))
        value = getattr(entry, 'value', None)
        if target is None:
            continue
        if isinstance(value, str):
            out.append("%s -> %s" % (target, value))
        else:
            out.append("%s -> (inline definition)" % target)
    return out


def _import_names(cfg) -> List[str]:
    out = []
    for entry in getattr(cfg, 'imports', None) or []:
        name = getattr(entry, 'name', None)
        if name is None and isinstance(entry, str):
            name = entry
        if name:
            out.append(name)
    return out


def extract_config(cfg, pkg=None) -> ConfigDoc:
    package = getattr(pkg, 'name', '') if pkg is not None else ''
    return ConfigDoc(
        name=getattr(cfg, 'name', ''),
        package=package,
        desc=getattr(cfg, 'desc', '') or '',
        doc=getattr(cfg, 'doc', '') or '',
        srcinfo=_srcref(cfg),
        uses=getattr(cfg, 'uses', None) or None,
        tasks=_target_names(getattr(cfg, 'tasks', None), package),
        types=_target_names(getattr(cfg, 'types', None), package),
        imports=_import_names(cfg),
        fragments=list(getattr(cfg, 'fragments', None) or []),
        overrides=_override_pairs(cfg),
    )


def documented_configs(pkg) -> List:
    """Every configuration. There is no visibility model for them.

    A configuration is selected by name from the command line, so anyone who
    can run the flow can select any of them. Hiding one would not make it
    unreachable -- it would only make it undiscoverable, which is the failure
    this tool exists to prevent.
    """
    return iter_configs(pkg)

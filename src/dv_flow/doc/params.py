"""Parameters, merged along `uses:` and annotated with where they came from.

This is the part of the extractor that earns the project: it replaces parameter
tables that were maintained by hand and were wrong the moment a base task
changed.

Everything here is assembled from engine contracts rather than re-derived
(ground rule §0.2):

    collect_task_params        the merged set, nearest declaration winning
    collect_param_value_sets   value sets, which inherit independently of values
    resolve_task_cli           the flags, including inherited and removed ones
    iter_uses_chain            the walk that provenance is read off

The one thing the engine does not answer is *which task declared a parameter*,
because nothing in the engine needs to know. Documentation does: a derived task
that changed one default should not read as though it redeclared the world.
"""

from typing import Any, Dict, List, Optional

from .model import CliDoc, ParamDoc, ValueDoc


def _type_name(ptype) -> str:
    """A readable type name. `param_defs.types` holds real Python types, so the
    unrendered form is `<class 'int'>` -- which is not what belongs in a table.
    """
    if ptype is None:
        return "any"
    name = getattr(ptype, '__name__', None)
    if name is not None:
        return name
    # typing constructs (Union[str, List], ...) have no __name__.
    return str(ptype).replace("typing.", "")


def declaring_tasks(task, param_name: str) -> List[str]:
    """Every task along `uses:` that declares `param_name`, nearest first.

    "Declares" means the parameter appears in that task's OWN `param_defs`, not
    in the merged view -- the merged view is what we are attributing.
    """
    from dv_flow.mgr.task import iter_uses_chain

    out = []
    for current in iter_uses_chain(task):
        param_defs = getattr(current, 'param_defs', None)
        if param_defs is None:
            continue
        if param_name in getattr(param_defs, 'definitions', {}):
            name = getattr(current, 'name', None)
            if name:
                out.append(name)
    return out


def provenance(task, param_name: str):
    """`(declared_by, overridden_by)` for `param_name`.

    `declared_by` is where the parameter was **introduced** -- the furthest task
    along `uses:` that declares it -- not the nearest one that mentions it.
    That distinction is the whole point of the field. Re-declaring a parameter
    to change its default is the common case, and crediting the derived task
    with the declaration would make it read "as if it redeclared the world",
    which is precisely what design §4.2 asks the rendering to avoid.

    `overridden_by` is the nearest task that re-declared it, when that is not
    the task that introduced it. It is what lets a page say "inherited from
    Base, default changed here" instead of silently showing a value that does
    not match the base's documentation.
    """
    chain = declaring_tasks(task, param_name)
    if not chain:
        return None, None
    declared_by = chain[-1]
    nearest = chain[0]
    return declared_by, (nearest if nearest != declared_by else None)


def _value_docs(value_set) -> List[ValueDoc]:
    if value_set is None:
        return []
    return [ValueDoc(value=getattr(v, 'value', v),
                     desc=getattr(v, 'desc', None) or "")
            for v in getattr(value_set, 'of', [])]


def _cli_doc(param_name: str, cli_args) -> Optional[CliDoc]:
    """The flag for `param_name`, from `resolve_task_cli`'s answer.

    Read from resolve_task_cli rather than from the ParamDef because that
    function is where flag inheritance and `cli: false` removal are decided. A
    parameter whose flag was removed by a derived task has a `cli:` declaration
    on its ParamDef and no flag; only one of those is true for the reader.
    """
    arg = cli_args.get(param_name)
    if arg is None:
        return None
    return CliDoc(
        name=getattr(arg, 'name', param_name) or param_name,
        short=getattr(arg, 'short', None) or None,
        hidden=bool(getattr(arg, 'hidden', False)))


def resolve_values(task, pkg, loader) -> Optional[Dict[str, Any]]:
    """`{param: resolved-value}`, or None when resolution is unavailable.

    Uses a throwaway `TaskGraphBuilder` that constructs no nodes, exactly as
    `dfm show task` does, so documenting a task never builds -- or fails on --
    that task's dependencies.

    Any failure returns None rather than raising. Ground rule §0.4: a docs build
    must never fail because a default happened to reference something
    unresolvable in the documentation environment. The caller falls back to the
    declared source text, which is still true, just less useful.
    """
    if pkg is None or loader is None:
        return None
    try:
        import os
        from dv_flow.mgr.task_graph_builder import TaskGraphBuilder
        builder = TaskGraphBuilder(
            root_pkg=pkg,
            rundir=os.path.join(os.getcwd(), "rundir"),
            loader=loader)
        return builder.resolveTaskParams(task)
    except Exception:
        return None


def extract_params(task, pkg=None, loader=None,
                   values: Optional[Dict[str, Any]] = None) -> List[ParamDoc]:
    """The documented parameters of `task`, in name order.

    Name order, not declaration order: a merged set has no single declaration
    order to preserve -- the parameters come from several tasks along the chain
    -- and an order that depends on which base a task happened to derive from
    would be worse than an arbitrary but stable one. `build_usage_info` sorts
    for the same reason, and matching it keeps the two views comparable.
    """
    from dv_flow.mgr.cli_args import resolve_task_cli
    from dv_flow.mgr.task import collect_task_params, collect_param_value_sets

    definitions, types = collect_task_params(task)
    value_sets = collect_param_value_sets(task)

    try:
        cli_args = {a.param: a for a in resolve_task_cli(task)}
    except Exception:
        cli_args = {}

    if values is None:
        values = resolve_values(task, pkg, loader)

    task_name = getattr(task, 'name', '')
    leaf = task_name.split('.')[-1] if '.' in task_name else task_name

    out: List[ParamDoc] = []
    for name in sorted(definitions.keys()):
        pdef = definitions[name]
        declared = getattr(pdef, 'value', None)

        resolved = declared
        default_expr = None
        if values is not None and name in values:
            resolved = values[name]
            # Only record the expression when it actually differs. Carrying
            # `default_expr` for every parameter would train a renderer to
            # ignore it, and it matters exactly where it appears.
            if isinstance(declared, str) and "${{" in declared \
                    and str(resolved) != declared:
                default_expr = declared

        vs = value_sets.get(name)
        declared_by, overridden_by = provenance(task, name)

        out.append(ParamDoc(
            name=name,
            type=_type_name(types.get(name)),
            default=resolved,
            default_expr=default_expr,
            desc=getattr(pdef, 'desc', None) or "",
            doc=getattr(pdef, 'doc', None) or "",
            declared_by=declared_by or "",
            overridden_by=overridden_by,
            inherited=(declared_by is not None and declared_by != task_name),
            values=_value_docs(vs),
            values_open=bool(getattr(vs, 'open', False)) if vs else False,
            cli=_cli_doc(name, cli_args),
            # Every parameter is reachable with -D, whether or not it has a
            # flag. That is the point of showing it (design §4.1).
            define="-D %s.%s=VALUE" % (leaf, name),
        ))

    return out

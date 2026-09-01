"""Turning a loaded `Task` into a `TaskDoc`.

The seam the whole project rests on: past this function, nothing touches engine
objects. Everything a renderer needs is plain data, and everything that is not
here is not renderable -- which is the right pressure, because it forces gaps
in the extraction contract to show up as missing data rather than as a renderer
quietly reaching back into the model.
"""

from typing import Any, Dict, List, Optional

from .classify import classify, facets, scope_of
from .model import (ExampleDoc, ProducesDoc, SrcRef, TagDoc, TaskDoc)
from .params import extract_params, resolve_values


def _srcref(obj) -> Optional[SrcRef]:
    srcinfo = getattr(obj, 'srcinfo', None)
    if srcinfo is None:
        return None
    file = getattr(srcinfo, 'file', None)
    if not file:
        return None
    return SrcRef(file=file, line=getattr(srcinfo, 'lineno', None)
                  or getattr(srcinfo, 'line', 0) or 0)


def _uses_chain(task) -> List[str]:
    """Names along `uses:`, most-derived first, EXCLUDING the task itself.

    Excluding self because the chain is rendered as "this is built on ...", and
    a list whose first entry is the thing you are reading is noise.
    """
    from dv_flow.mgr.task import iter_uses_chain

    names = []
    for current in iter_uses_chain(task):
        if current is task:
            continue
        name = getattr(current, 'name', None)
        if name:
            names.append(name)
    return names


def _tag_docs(tags) -> List[TagDoc]:
    """Tags as name + the parameters they were applied with.

    A resolved tag is a `Type` whose `paramT` is an INSTANCE, not a class --
    the parameters are already bound. Stringifying the tag instead (which is
    what the CLI used to do) yields a repr blob that a consumer can only regex
    at, and would make the lifecycle tags unreadable exactly where they matter.
    """
    out = []
    for tag in tags or []:
        name = getattr(tag, 'name', None)
        if name is None:
            out.append(TagDoc(name=str(tag)))
            continue
        params: Dict[str, Any] = {}
        paramT = getattr(tag, 'paramT', None)
        model_fields = getattr(type(paramT), 'model_fields', None) if paramT is not None else None
        for field in (model_fields or {}):
            value = getattr(paramT, field, None)
            params[field] = value if isinstance(
                value, (str, int, float, bool, list, dict)) or value is None else str(value)
        out.append(TagDoc(name=name, params=params))
    return out


def _produces_docs(produces) -> List[ProducesDoc]:
    """`produces:` entries, split into type, attributes and prose.

    `type` is the item type. `doc` is prose about the specific artifact and is
    NOT an attribute -- the engine excludes it from matching and from
    expression evaluation, and the extraction has to make the same split or the
    renderer would show a task's documentation as something a consumer can
    match on. Everything else IS an attribute (`filetype`, and whatever a
    package invents).
    """
    out = []
    for entry in produces or []:
        if isinstance(entry, dict):
            attrs = {k: v for k, v in entry.items()
                     if k not in ('type',) and k not in _NON_ATTRIBUTE_KEYS}
            out.append(ProducesDoc(
                type=str(entry.get('type', '')),
                attrs=attrs,
                doc=str(entry.get('doc', '') or '')))
        else:
            # `produces: std.FileSet` -- shorthand for `{type: std.FileSet}`.
            out.append(ProducesDoc(type=str(entry)))
    return out


def _non_attribute_keys():
    try:
        from dv_flow.mgr.type_match import NON_ATTRIBUTE_KEYS
        return set(NON_ATTRIBUTE_KEYS)
    except ImportError:
        # Older dv-flow-mgr. `doc` is inert there -- it would show as an
        # attribute rather than as prose, which is wrong but not harmful.
        return {'doc'}


_NON_ATTRIBUTE_KEYS = _non_attribute_keys()


def _example_docs(examples, srcinfo=None) -> List[ExampleDoc]:
    """Authored examples, carrying the declaring task's location.

    The location is the task, not the example: `ExampleDef` records none of its
    own. It is close enough to be actionable -- a validation failure has to send
    the reader to the flow file that contains the broken snippet, and "this
    task, in this file" is where they will start looking anyway.
    """
    return [ExampleDoc(
        title=getattr(ex, 'title', None),
        code=getattr(ex, 'code', '') or '',
        caption=getattr(ex, 'caption', None),
        lang=getattr(ex, 'lang', 'yaml') or 'yaml',
        origin='flow',
        srcinfo=srcinfo)
        for ex in examples or []]


def _behavior(task) -> Dict[str, Any]:
    """The collapsed facts table (design §4.2).

    Only what was actually set: a table of engine defaults tells the reader
    nothing and crowds out the one row that does.
    """
    out: Dict[str, Any] = {}

    rundir = getattr(task, 'rundir', None)
    if rundir is not None:
        out['rundir'] = getattr(rundir, 'value', None) or str(rundir)

    for field in ('uptodate', 'cache', 'on_error', 'elaborate'):
        value = getattr(task, field, None)
        if value is not None:
            out[field] = value if isinstance(
                value, (str, int, float, bool)) else str(value)

    max_failures = getattr(task, 'max_failures', -1)
    if max_failures != -1:
        out['max_failures'] = max_failures

    run = getattr(task, 'run', None)
    if run:
        out['run'] = run
        out['shell'] = getattr(task, 'shell', 'bash')

    return out


def _collect_requires(task):
    try:
        from dv_flow.mgr.task import collect_task_requires
        return collect_task_requires(task)
    except ImportError:
        # Older dv-flow-mgr without the shared helper (upstream U12). Fall back
        # to what the task declares itself: under-reporting an inherited
        # contract is better than failing to document the task at all.
        return getattr(task, 'requires', None)


def _needs(task) -> List[str]:
    out = []
    for need in getattr(task, 'needs', []) or []:
        name = getattr(need, 'name', None)
        if name is None:
            inner = getattr(need, 'task', None)
            name = getattr(inner, 'name', None) if inner is not None else None
        out.append(name if name else str(need))
    return out


def extract_task(task, pkg=None, loader=None,
                 values: Optional[Dict[str, Any]] = None,
                 index=None) -> TaskDoc:
    """The documentation document for `task`.

    `values` may be passed in when the caller already resolved them (a package
    extraction resolves once and reuses); otherwise resolution is attempted
    here and degrades to declared text on any failure.

    `index` is a `ReverseIndex`. Optional because a single-task extraction
    should not have to walk the whole package to answer a question the page may
    not even ask -- but on an abstract task it is what supplies the known
    implementations.
    """
    kind = classify(task)
    name = getattr(task, 'name', '')
    package = getattr(getattr(task, 'package', None), 'name', '')

    if values is None:
        values = resolve_values(task, pkg, loader)

    doc = TaskDoc(
        kind=kind,
        name=name,
        package=package,
        desc=getattr(task, 'desc', '') or '',
        doc=getattr(task, 'doc', '') or '',
        scope=scope_of(task),
        facets=facets(task),
        srcinfo=_srcref(task),
        uses_chain=_uses_chain(task),
        params=extract_params(task, pkg, loader, values=values),
        consumes=getattr(task, 'consumes', None),
        consumes_declared=bool(getattr(task, 'consumes_declared', False)),
        produces=_produces_docs(getattr(task, 'produces', None)),
        passthrough=getattr(task, 'passthrough', None),
        needs=_needs(task),
        tags=_tag_docs(getattr(task, 'tags', None)),
        # Accumulated along `uses:` via the engine's own helper, not read off
        # the task: a leaf that uses a capability that uses an archetype is
        # subject to all three levels, and showing only what the task declared
        # itself would under-report the contract a reader has to satisfy.
        requires=_tag_docs(_collect_requires(task)),
        examples=_example_docs(getattr(task, 'examples', None), _srcref(task)),
        behavior=_behavior(task),
    )

    if index is not None:
        doc.implementations = list(index.implementations.get(name, []))

    # The CLI view is carried VERBATIM from the engine rather than rebuilt from
    # `doc.params`. Ground rule §0.2: `dfm show task --usage` and the rendered
    # option list must answer the same question the same way, and two
    # derivations of "what flags does this task have" would eventually disagree
    # -- with the docs being the half nobody notices is wrong.
    # An abstract task gets no CLI view even when it declares `scope: root`.
    # It cannot be run -- `abstract` beats `root` in the classification cascade
    # for exactly this reason -- so offering a command line would be an
    # invitation to an error the page itself caused.
    if 'root' in doc.scope and kind != 'abstract':
        try:
            from dv_flow.mgr.cmds.show.usage import build_usage_info
            doc.usage = build_usage_info(task, values=values)
        except Exception:
            doc.usage = None

    return doc

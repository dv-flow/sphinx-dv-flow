"""The extraction contract (design §7).

One intermediate document per documented object, JSON-serializable, produced by
the extractors and consumed by renderers. **Renderers never touch `Task`
objects.** That seam is what makes the extractor golden-testable without Sphinx,
gives `dvflow-doc dump` something real to print, and leaves a clean path if
extraction later moves upstream into `dfm show task --json`.

Two properties these dataclasses have to hold:

*Stable key order.* `to_dict()` emits keys in field-declaration order, and the
golden tests compare serialized output. Reordering a field is therefore a
visible change, which is the point: the contract is an interface, and it should
be as awkward to reshuffle as any other.

*Absence is representable.* Several fields distinguish "not declared" from
"declared empty" -- `consumes_declared` is the clearest case. A renderer that
cannot tell those apart will state a contract the author never made, so the
model keeps them apart even where it makes the dataclass wordier.
"""

import dataclasses as dc
from typing import Any, Dict, List, Optional


def _to_jsonable(value):
    """Recursively convert to JSON-safe data, preserving field order."""
    if dc.is_dataclass(value) and not isinstance(value, type):
        return value.to_dict()
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # Enums, pydantic models, engine objects: stringify rather than fail. A
    # document that renders is worth more than one that raises over a field a
    # renderer may not even read.
    return str(value)


@dc.dataclass
class _Doc:
    """Serialization shared by every document in the contract."""

    def to_dict(self) -> Dict[str, Any]:
        return {f.name: _to_jsonable(getattr(self, f.name))
                for f in dc.fields(self)}


@dc.dataclass
class SrcRef(_Doc):
    """Where something was written. `file` is absolute; renderers relativize."""
    file: str = ""
    line: int = 0


@dc.dataclass
class ValueDoc(_Doc):
    """One member of a parameter's value set."""
    value: Any = None
    desc: str = ""


@dc.dataclass
class CliDoc(_Doc):
    """How a parameter appears on the command line.

    Only present when the parameter actually has a flag. `hidden` options are
    extracted but are the renderer's business to omit -- dropping them here
    would leave no way to document them deliberately.
    """
    name: str = ""
    short: Optional[str] = None
    hidden: bool = False


@dc.dataclass
class ParamDoc(_Doc):
    """A parameter, as documented within its owner. Never a page of its own."""
    name: str = ""
    type: str = "any"
    # `default` is the RESOLVED value where a builder was available;
    # `default_expr` is the source text it came from, present only when the two
    # differ. Showing only the expression is useless to a reader; showing only
    # the resolved value hides that it tracks a package variable (design §4.1).
    default: Any = None
    default_expr: Optional[str] = None
    desc: str = ""
    doc: str = ""
    # Where the parameter was INTRODUCED -- the furthest task along `uses:`
    # that declares it -- not the nearest one that mentions it. Re-declaring a
    # parameter to change one default is the common case, and crediting the
    # derived task with the declaration would make it read as if it had
    # redeclared the world (design §4.2).
    declared_by: str = ""
    # The nearest task that re-declared it, when that is not where it was
    # introduced. This is what lets a page say "inherited from Base, default
    # changed here" rather than showing a value that quietly disagrees with the
    # base's documentation.
    overridden_by: Optional[str] = None
    inherited: bool = False
    # NOTE: there is deliberately no `required` field, though design §4.1 asked
    # for one. The engine substitutes a type default ("" / 0 / []) at load, so
    # "declared without `value:`" is erased before anything can read it -- and
    # more to the point, a task whose parameter has no authored default still
    # runs. Marking such a parameter "required" would promise enforcement that
    # does not exist. See PLAN.md §5 U10.
    values: List[ValueDoc] = dc.field(default_factory=list)
    # An OPEN set enumerates the known values without forbidding the rest.
    # Rendering one as exhaustive is a lie a reader cannot detect.
    values_open: bool = False
    cli: Optional[CliDoc] = None
    # Always present: every parameter is reachable with -D, not just the ones
    # that were given flags.
    define: str = ""


@dc.dataclass
class ExampleDoc(_Doc):
    """A worked example.

    Nothing *runs* an example -- but a flow-fragment example is **loaded**, and
    that distinction is the whole of §9's validation story: an example that no
    longer parses is worse than no example, because it is indistinguishable
    from one that works until someone types it.
    """
    title: Optional[str] = None
    code: str = ""
    caption: Optional[str] = None
    lang: str = "yaml"
    # Where the example came from: 'flow' (an `examples:` entry), 'file' (an
    # adjacent `.rst`), or 'generated'. Rendered, because a generated example is
    # a synthesis of the declaration rather than something anyone asserted
    # works, and a reader who cannot tell them apart will trust both equally.
    origin: str = "flow"
    srcinfo: Optional[SrcRef] = None
    # None when the example was not checked -- it is not a flow fragment, or
    # validation was switched off. `False` with `error` set when the engine
    # refused it. Three states, because "not checked" and "checked and fine"
    # are different claims and only one of them is worth making.
    valid: Optional[bool] = None
    error: str = ""


@dc.dataclass
class TagDoc(_Doc):
    """A tag type applied to a task, with the parameters it was applied with."""
    name: str = ""
    params: Dict[str, Any] = dc.field(default_factory=dict)


@dc.dataclass
class ProducesDoc(_Doc):
    """One entry of a `produces:` declaration.

    `produces` declares what MAY be produced, not what always is. The heading
    says so once; individual rows are not hedged (design §4.2).
    """
    type: str = ""
    attrs: Dict[str, Any] = dc.field(default_factory=dict)
    # Prose describing the specific artifact, from `doc:` on the entry --
    # typically the path it lands at ("${{ task_rundir }}/ral_pkg.sv").
    #
    # The item TYPE says what kind of thing this is, which is the minimum a
    # consumer needs; this says which thing, which is what a person needs. It
    # is carried unevaluated on purpose: the shape of the path documents the
    # output, where one machine's resolution of it does not.
    doc: str = ""


@dc.dataclass
class TaskDoc(_Doc):
    """A task, in whichever of the §4 kinds it classified as."""
    kind: str = "internal"
    name: str = ""
    package: str = ""
    desc: str = ""
    doc: str = ""
    scope: List[str] = dc.field(default_factory=list)
    # Orthogonal annotations that do not replace the kind: 'pytask', 'shell',
    # 'elaborate', ... (design §4.0).
    facets: List[str] = dc.field(default_factory=list)
    srcinfo: Optional[SrcRef] = None
    # Most-derived first, EXCLUDING the task itself.
    uses_chain: List[str] = dc.field(default_factory=list)
    params: List[ParamDoc] = dc.field(default_factory=list)
    # Verbatim `build_usage_info()`, root kinds only. Verbatim because ground
    # rule §0.2 says the CLI view has one source, and re-deriving it here would
    # make two.
    usage: Optional[Dict[str, Any]] = None
    consumes: Any = None
    # Whether `consumes:` was declared at all -- including inherited through
    # `uses:`, which IS a declaration. `consumes` itself is defaulted by the
    # engine, so it cannot answer this, and reading the default as an authored
    # claim is what makes a dataflow contract vacuous.
    consumes_declared: bool = False
    produces: List[ProducesDoc] = dc.field(default_factory=list)
    passthrough: Any = None
    needs: List[str] = dc.field(default_factory=list)
    tags: List[TagDoc] = dc.field(default_factory=list)
    requires: List[TagDoc] = dc.field(default_factory=list)
    examples: List[ExampleDoc] = dc.field(default_factory=list)
    # rundir, uptodate, cache, shell, ... -- the collapsed facts table.
    behavior: Dict[str, Any] = dc.field(default_factory=dict)
    # Tasks naming this one in `uses:`. Filled from the reverse index; empty
    # when none was supplied. On an abstract task this is "known
    # implementations", which is the most useful thing an extension point can
    # tell a reader -- and it is not answerable from the task's own
    # declaration, because `uses:` points the other way.
    implementations: List[str] = dc.field(default_factory=list)


@dc.dataclass
class TypeDoc(_Doc):
    """A data type: the vocabulary `produces`/`consumes` speak."""
    kind: str = "type"
    name: str = ""
    package: str = ""
    doc: str = ""
    srcinfo: Optional[SrcRef] = None
    uses_chain: List[str] = dc.field(default_factory=list)
    params: List[ParamDoc] = dc.field(default_factory=list)
    # 'check' (a graph-build contract) and/or 'tag' (derives from std.Tag).
    # Both change what a reader should DO with the type, not merely how it is
    # described, so they are facets rather than a note in the prose.
    facets: List[str] = dc.field(default_factory=list)
    tags: List[TagDoc] = dc.field(default_factory=list)
    # For a check type, the `module:function` implementing it.
    check: Optional[str] = None
    # Filled in from the reverse index (`indices.py`) when one is supplied.
    # These are the questions a type page mostly exists to answer, and none of
    # them is answerable from the type's own declaration -- the arrows all point
    # the other way.
    produced_by: List[str] = dc.field(default_factory=list)
    consumed_by: List[str] = dc.field(default_factory=list)
    derived_by: List[str] = dc.field(default_factory=list)


@dc.dataclass
class ConfigDoc(_Doc):
    """A named configuration: a pre-selected way to load a package.

    What a reader needs from a configuration is not how it is implemented but
    two things: what it changes, and what to type to get it. Everything here
    serves one of those.

    Deliberately absent: the parameters it fixes. `ConfigDef.params` is typed
    as a list while the merge that consumes it implements only the map form, so
    neither spelling does anything (PLAN.md U15). A page showing "parameters
    this configuration fixes" would be describing a mechanism that does not
    run -- which is worse than saying nothing, because the reader cannot tell.
    """
    kind: str = "config"
    name: str = ""
    package: str = ""
    desc: str = ""
    doc: str = ""
    srcinfo: Optional[SrcRef] = None
    # The configuration this one builds on, when it declares `uses:`.
    uses: Optional[str] = None
    # Task and type names this configuration redefines. Names only: what the
    # override *is* belongs to the config, but a reader chasing it wants the
    # task's own page, which documents the task as loaded by default.
    tasks: List[str] = dc.field(default_factory=list)
    types: List[str] = dc.field(default_factory=list)
    # Extra imports and fragments the configuration pulls in. Named, not
    # expanded: what a fragment contains depends on selecting the config, and
    # the package as loaded here does not have it.
    imports: List[str] = dc.field(default_factory=list)
    fragments: List[str] = dc.field(default_factory=list)
    # Package-level `overrides:` entries, as "target -> replacement".
    overrides: List[Any] = dc.field(default_factory=list)


@dc.dataclass
class FilterDoc(_Doc):
    """A filter: a named transformation usable on the right of a `|`.

    The signature is the thing a reader is here for -- a filter is invoked in
    an expression, and what has to be typed is the whole interface.
    """
    kind: str = "filter"
    name: str = ""
    package: str = ""
    desc: str = ""
    doc: str = ""
    srcinfo: Optional[SrcRef] = None
    scope: List[str] = dc.field(default_factory=list)
    params: List[ParamDoc] = dc.field(default_factory=list)
    # 'expr' (a jq-style expression) or 'run' (a script). Which one it is
    # changes what the filter can do, so it is a facet rather than prose.
    impl: str = "expr"
    # The implementation itself. Shown because a filter is small enough that
    # its source IS its specification, and because `expr` is the only place
    # positional `$arg0` binding is visible.
    body: str = ""
    shell: str = ""
    # How it is written at a call site: `${{ inputs | by_arch(arch) }}`. Built
    # by extraction rather than by a renderer so that every renderer shows the
    # same call, and so `dvflow-doc dump` carries it.
    signature: str = ""


@dc.dataclass
class PackageDoc(_Doc):
    """A package: the landing page for a flow library."""
    kind: str = "package"
    name: str = ""
    desc: str = ""
    doc: str = ""
    srcinfo: Optional[SrcRef] = None
    # Names only. The documents themselves are separate, so a renderer decides
    # what to inline and a `dump` of one package does not drag in every task.
    tasks: List[str] = dc.field(default_factory=list)
    types: List[str] = dc.field(default_factory=list)
    configs: List[str] = dc.field(default_factory=list)
    filters: List[str] = dc.field(default_factory=list)
    imports: List[str] = dc.field(default_factory=list)
    # `[(kind, [task-name])]` in reading order -- what can I run, what can I
    # build with, what can I extend. The grouping is extraction's business
    # because the kind cascade is; the headings are the renderer's.
    groups: List[Any] = dc.field(default_factory=list)

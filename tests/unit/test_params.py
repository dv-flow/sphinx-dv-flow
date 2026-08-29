"""Parameter extraction: the merged set, its provenance, and its defaults.

This is the milestone's payload -- the thing that replaces parameter tables
maintained by hand. Every assertion here is about something a reader would be
misled by if it were wrong, not about the shape of the dataclass.
"""

import pytest

from dv_flow.doc.params import declaring_tasks, extract_params, provenance


def _params(loaded, fixture, task_name):
    result = loaded[fixture]
    task = result.pkg.task_m[task_name]
    return {p.name: p
            for p in extract_params(task, result.pkg, result.loader)}


# --------------------------------------------------------- the merged set

def test_inherited_params_are_present(loaded):
    """A derived task really HAS its base's params -- they are in its paramT
    and settable with -D -- so listing only its own declarations under-reports
    it. This is the whole reason the extractor uses `collect_task_params`."""
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert set(params) == {
        "from_base", "from_middle", "overridden", "flag_removed", "own"}


def test_params_are_name_ordered(loaded):
    """A merged set has no single declaration order to preserve.

    An order that depended on which base a task happened to derive from would
    be worse than an arbitrary but stable one, and `build_usage_info` sorts for
    the same reason -- matching it keeps the two views comparable.
    """
    result = loaded["inherit"]
    names = [p.name for p in extract_params(
        result.pkg.task_m["inherit.Leaf"], result.pkg, result.loader)]
    assert names == sorted(names)


# ------------------------------------------------------------- provenance

def test_provenance_names_the_declaring_task(loaded):
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert params["from_base"].declared_by == "inherit.Base"
    assert params["from_middle"].declared_by == "inherit.Middle"
    assert params["own"].declared_by == "inherit.Leaf"


def test_provenance_reaches_past_the_immediate_base(loaded):
    """Two levels up, not one. `from_base` is declared in Base and Leaf uses
    Middle, so a one-level walk would credit Middle -- or nothing."""
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert params["from_base"].declared_by == "inherit.Base"
    assert params["from_base"].inherited is True


def test_own_params_are_not_marked_inherited(loaded):
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert params["own"].inherited is False
    assert params["own"].overridden_by is None


def test_a_changed_default_does_not_claim_the_declaration(loaded):
    """The point of origin-based provenance (design §4.2).

    Leaf re-declares `overridden` to change one default. Crediting Leaf with
    the declaration would make it read as though it had redeclared the world --
    exactly what the design says the rendering must avoid. The override is
    reported separately, so nothing is lost.
    """
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert params["overridden"].declared_by == "inherit.Base"
    assert params["overridden"].inherited is True
    assert params["overridden"].overridden_by == "inherit.Leaf"


def test_declaring_tasks_lists_the_whole_chain_nearest_first(loaded):
    result = loaded["inherit"]
    chain = declaring_tasks(result.pkg.task_m["inherit.Leaf"], "overridden")
    assert chain == ["inherit.Leaf", "inherit.Base"]


def test_provenance_of_an_undeclared_param_is_empty(loaded):
    result = loaded["inherit"]
    assert provenance(result.pkg.task_m["inherit.Leaf"], "nope") == (None, None)


# ----------------------------------------------------------------- defaults

def test_a_derived_default_wins(loaded):
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert params["overridden"].default == "leaf-default"


def test_the_base_default_survives_where_nothing_overrode_it(loaded):
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert params["from_base"].default == "base-value"
    assert params["from_middle"].default == 7


def test_an_expression_default_carries_both_forms(loaded):
    """Showing only `${{ build }}` is useless to a reader; showing only `opt`
    hides that it tracks a package variable (design §4.1)."""
    params = _params(loaded, "simple", "simple.run")
    assert params["build"].default == "opt"
    assert params["build"].default_expr == "${{ build }}"


def test_a_literal_default_carries_no_expression(loaded):
    """`default_expr` present on every row would train a renderer to ignore it,
    and it matters exactly where it appears."""
    params = _params(loaded, "simple", "simple.run")
    assert params["top"].default == "tb_top"
    assert params["top"].default_expr is None


def test_a_valueless_param_gets_the_type_default(loaded):
    """Pins that there is no "required" concept to document.

    The engine substitutes the type default at load, so "declared without
    `value:`" is erased before anything can read it -- and the task runs
    regardless. Reporting such a parameter as required would promise
    enforcement that does not exist. See PLAN.md §5 U10.
    """
    params = _params(loaded, "simple", "simple.run")
    assert params["name"].default == ""
    assert not hasattr(params["name"], "required")


# --------------------------------------------------------------- value sets

def test_a_value_set_inherits_independently_of_the_value(loaded):
    """The engine's documented rule, and the case most likely to be dropped.

    Leaf re-declares `overridden` with only a new default and says nothing
    about `values:`, so it keeps -- and is checked against -- Base's set.
    """
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert [v.value for v in params["overridden"].values] == [
        "base-default", "leaf-default", "third"]


def test_value_docs_survive(loaded):
    """A value set is often the only place the meaning of a value is written
    down; dropping the per-value text leaves nothing to replace the prose."""
    params = _params(loaded, "simple", "simple.run")
    docs = {v.value: v.desc for v in params["mode"].values}
    assert docs["quiet"] == "Errors only."
    assert docs["full"] == "Everything, including per-step timing."


def test_an_open_set_is_marked_open(loaded):
    """An open set enumerates KNOWN values without forbidding the rest.

    Rendering one as exhaustive is a lie the reader cannot detect, so the flag
    has to reach the renderer.
    """
    params = _params(loaded, "simple", "simple.run")
    assert params["backend"].values_open is True
    assert [v.value for v in params["backend"].values] == ["vlt", "vcs"]


def test_a_closed_set_is_not_marked_open(loaded):
    params = _params(loaded, "simple", "simple.run")
    assert params["mode"].values_open is False


def test_no_value_set_is_an_empty_list(loaded):
    params = _params(loaded, "simple", "simple.run")
    assert params["top"].values == []
    assert params["top"].values_open is False


# ------------------------------------------------------------- CLI options

def test_a_flag_is_reported(loaded):
    params = _params(loaded, "simple", "simple.run")
    assert params["mode"].cli is not None
    assert params["mode"].cli.name == "mode"


def test_a_short_option_is_reported(loaded):
    params = _params(loaded, "simple", "simple.run")
    assert params["jobs"].cli.short == "J"


def test_a_param_without_a_flag_has_no_cli(loaded):
    params = _params(loaded, "simple", "simple.run")
    assert params["top"].cli is None


def test_a_hidden_flag_is_extracted_not_dropped(loaded):
    """Omitting a hidden option is the renderer's decision.

    Dropping it here would leave no way to document one deliberately, and the
    parameter would look like it had no flag at all -- which is a different
    statement.
    """
    params = _params(loaded, "simple", "simple.run")
    assert params["secret"].cli is not None
    assert params["secret"].cli.hidden is True


def test_cli_false_removes_the_flag_but_keeps_the_param(loaded):
    """Leaf sets `cli: false`. The flag goes; the parameter stays, still
    settable with -D, and still documented."""
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert params["flag_removed"].cli is None
    assert params["flag_removed"].define == "-D Leaf.flag_removed=VALUE"


def test_an_inherited_flag_survives(loaded):
    params = _params(loaded, "inherit", "inherit.Leaf")
    assert params["overridden"].cli is not None


# ------------------------------------------------------------ define strings

def test_every_param_has_a_define(loaded):
    """The point of the Parameters block: EVERY parameter is reachable, not
    only the ones that were given flags (design §4.1)."""
    params = _params(loaded, "simple", "simple.run")
    for name, p in params.items():
        assert p.define == "-D run.%s=VALUE" % name


# ------------------------------------------------------------- degradation

def test_extraction_works_without_a_builder(loaded):
    """No builder means no resolved values -- not a failure.

    Ground rule §0.4: a docs build must never fail because a default referenced
    something unresolvable here. It degrades to the declared source text, which
    is still true, just less useful.
    """
    result = loaded["simple"]
    params = {p.name: p for p in extract_params(
        result.pkg.task_m["simple.run"], pkg=None, loader=None)}
    assert params["build"].default == "${{ build }}"
    assert params["build"].default_expr is None
    assert params["top"].default == "tb_top"

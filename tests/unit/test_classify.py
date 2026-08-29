"""The §4.0 classification cascade.

Worth testing branch by branch because a misclassification does not fail --
it silently renders the wrong page. The order of the cascade is the substance,
so most of these tests are about which rule beats which.

These use stand-in objects rather than loaded tasks. The cascade reads a handful
of attributes and nothing else; constructing a real `select:` family or an
abstract task through the loader for each case would test the loader, obscure
what each rule actually depends on, and make an ordering test read as an
accident of fixture design.
"""

import pytest

from dv_flow.doc.classify import (
    DEFAULT_KINDS, classify, facets, is_documented_by_default, scope_of)


class FakeTask:
    def __init__(self, **kw):
        self.abstract = False
        self.strategy = None
        self.select_bindings = None
        self.subtasks = []
        self.is_root = False
        self.is_export = False
        self.is_local = False
        self.shell = "bash"
        self.run = None
        self.elaborate = None
        self.requires = []
        self.needs = []
        for k, v in kw.items():
            setattr(self, k, v)


class FakeStrategy:
    def __init__(self, select=None):
        self.select = select


# ------------------------------------------------------------ the plain cases

def test_root():
    assert classify(FakeTask(is_root=True)) == "root"


def test_library():
    assert classify(FakeTask(is_export=True)) == "library"


def test_internal_is_the_fallthrough():
    assert classify(FakeTask()) == "internal"


def test_compound():
    assert classify(FakeTask(subtasks=[object()])) == "compound"


def test_abstract():
    assert classify(FakeTask(abstract=True)) == "abstract"


def test_variant_family():
    assert classify(FakeTask(strategy=FakeStrategy(select=object()))) == "variants"


def test_variant_cell():
    assert classify(FakeTask(select_bindings={"sim": "vlt"})) == "variant-cell"


# --------------------------------------------------------------- the ordering

def test_abstract_beats_root():
    """An abstract task is an extension point even when it declares a scope.

    "Derive from this" is what a reader needs; "run this" is not available.
    """
    assert classify(FakeTask(abstract=True, is_root=True)) == "abstract"


def test_abstract_beats_compound():
    assert classify(FakeTask(abstract=True, subtasks=[object()])) == "abstract"


def test_select_family_beats_compound():
    """A family may have a body, but what a reader addresses is the cells."""
    task = FakeTask(strategy=FakeStrategy(select=object()), subtasks=[object()])
    assert classify(task) == "variants"


def test_a_cell_is_suppressed_even_when_root():
    """Cells of a `root:` family are runnable, and still not separate pages.

    Giving each cell of a 3x4 lattice its own page would bury the family that
    explains what the cells mean.
    """
    task = FakeTask(select_bindings={"sim": "vlt"}, is_root=True)
    assert classify(task) == "variant-cell"


def test_compound_beats_root():
    """The sub-flow is the interesting content; scope survives as a badge."""
    task = FakeTask(subtasks=[object()], is_root=True)
    assert classify(task) == "compound"
    assert scope_of(task) == ["root"]


def test_root_beats_export():
    task = FakeTask(is_root=True, is_export=True)
    assert classify(task) == "root"


# -------------------------------------------------------------------- scope

def test_scope_order_is_stable():
    task = FakeTask(is_root=True, is_export=True, is_local=True)
    assert scope_of(task) == ["root", "export", "local"]


def test_no_scope_is_empty():
    assert scope_of(FakeTask()) == []


# ------------------------------------------------------------------- facets

def test_pytask_facet():
    task = FakeTask(run="mod:fn", shell="pytask")
    assert "pytask" in facets(task)
    assert "shell" not in facets(task)


def test_shell_facet():
    task = FakeTask(run="echo hi", shell="bash")
    assert "shell" in facets(task)
    assert "pytask" not in facets(task)


def test_no_run_means_no_implementation_facet():
    assert facets(FakeTask()) == []


def test_facets_do_not_replace_the_kind():
    """A facet annotates; it never changes what page you get."""
    task = FakeTask(is_root=True, run="mod:fn", shell="pytask",
                    elaborate="mod:elab")
    assert classify(task) == "root"
    assert set(facets(task)) >= {"pytask", "elaborate"}


def test_root_and_export_is_flagged_as_also_library():
    """Both audiences have to survive classification into a single kind.

    A root+export task gets the CLI view and then a "using this in a flow"
    section (design §4.1); without this facet the second audience is invisible.
    """
    assert "also-library" in facets(FakeTask(is_root=True, is_export=True))


def test_root_alone_is_not_also_library():
    assert "also-library" not in facets(FakeTask(is_root=True))


# ------------------------------------------------------- inclusion by default

def test_local_is_never_documented():
    """Even as a root task: a fragment-scoped name is not addressable."""
    assert not is_documented_by_default(FakeTask(is_local=True, is_root=True))


def test_internal_is_excluded_by_default():
    assert not is_documented_by_default(FakeTask())


def test_variant_cells_are_excluded_by_default():
    assert not is_documented_by_default(FakeTask(select_bindings={"a": 1}))


@pytest.mark.parametrize("kw,kind", [
    ({"is_root": True}, "root"),
    ({"is_export": True}, "library"),
    ({"abstract": True}, "abstract"),
    ({"subtasks": [object()]}, "compound"),
])
def test_the_default_kinds_are_documented(kw, kind):
    task = FakeTask(**kw)
    assert classify(task) == kind
    assert kind in DEFAULT_KINDS
    assert is_documented_by_default(task)

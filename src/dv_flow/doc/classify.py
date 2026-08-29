"""Which of the §4 documentation kinds a task belongs to.

Pure functions over a loaded `Task`. Nothing here loads, resolves, or renders,
which is what makes the cascade cheap to test exhaustively -- and the cascade is
worth testing exhaustively, because a misclassification does not fail: it
silently produces the wrong page.
"""

KIND_ABSTRACT = "abstract"
KIND_VARIANTS = "variants"
KIND_VARIANT_CELL = "variant-cell"
KIND_COMPOUND = "compound"
KIND_ROOT = "root"
KIND_LIBRARY = "library"
KIND_INTERNAL = "internal"

# Kinds documented by default. `variant-cell` is excluded because a cell is
# folded into its family's page: giving each cell of a 3x4 lattice its own page
# would bury the family that explains them.
DEFAULT_KINDS = (KIND_ABSTRACT, KIND_VARIANTS, KIND_COMPOUND,
                 KIND_ROOT, KIND_LIBRARY)


def classify(task) -> str:
    """The documentation kind of `task`. First match wins (design §4.0).

    Order is the substance of this function, not an implementation detail:

    - `abstract` beats `root`, because an abstract task is an extension point
      even if it also declares a scope. What a reader needs is "derive from
      this", not "run this" -- and running it is not, in fact, available.
    - a `select:` family beats `compound`: a family may have a body, but the
      thing a reader addresses is the set of cells.
    - a cell is suppressed entirely, folded into its family.
    - `compound` beats `root`/`export`, because the sub-flow IS the interesting
      content; scope still shows up as a badge, so nothing is lost.
    """
    if getattr(task, 'abstract', False):
        return KIND_ABSTRACT

    if getattr(getattr(task, 'strategy', None), 'select', None) is not None:
        return KIND_VARIANTS

    if getattr(task, 'select_bindings', None) is not None:
        return KIND_VARIANT_CELL

    if getattr(task, 'subtasks', None):
        return KIND_COMPOUND

    if getattr(task, 'is_root', False):
        return KIND_ROOT

    if getattr(task, 'is_export', False):
        return KIND_LIBRARY

    return KIND_INTERNAL


def scope_of(task):
    """The declared visibility scopes, in the order the design tables use them.

    This doubles as the documentation-audience model (design §3): `root` means
    a CLI page, `export` a library page, neither means package-internal.
    """
    scope = []
    if getattr(task, 'is_root', False):
        scope.append('root')
    if getattr(task, 'is_export', False):
        scope.append('export')
    if getattr(task, 'is_local', False):
        scope.append('local')
    return scope


def facets(task):
    """Orthogonal annotations that describe a task without replacing its kind.

    A facet answers "how is this implemented / how does it behave", where the
    kind answers "what is this for". Keeping them separate is what stops the
    cascade from growing a branch per combination.
    """
    out = []

    shell = getattr(task, 'shell', None)
    run = getattr(task, 'run', None)
    if run:
        # `shell: pytask` means `run` names a Python entry point rather than a
        # command line -- a distinction a reader needs before trying to read it.
        out.append('pytask' if shell == 'pytask' else 'shell')

    if getattr(task, 'elaborate', None):
        out.append('elaborate')

    if getattr(task, 'requires', None):
        out.append('requires')

    if getattr(task, 'needs', None):
        out.append('needs')

    # A task may be both root and export: runnable, and also usable as a base.
    # It gets the CLI view first and a "using this in a flow" section after
    # (design §4.1), so the second audience has to survive classification.
    if getattr(task, 'is_root', False) and getattr(task, 'is_export', False):
        out.append('also-library')

    return out


def is_documented_by_default(task) -> bool:
    """Whether `task` appears without an explicit opt-in.

    Visibility drives inclusion (design §3): what is published stops being a
    documentation decision and becomes a consequence of a declaration the
    author already had to make. `local` is excluded always -- it is
    fragment-scoped, so it is not addressable by a reader under any option.
    """
    if getattr(task, 'is_local', False):
        return False
    return classify(task) in DEFAULT_KINDS

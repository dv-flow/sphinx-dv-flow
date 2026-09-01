"""Examples (design §9): where they come from, and whether they still work.

Extracted documentation is accurate but never sufficient -- nobody learns a task
from its parameter table. §9 names three sources; this module supplies the two
that are not simply a field on the task, plus the validation that keeps any of
them from rotting.

**On precedence.** §9 lists the sources "in precedence order", and the
*generated* snippet does yield to both authored forms -- it exists to fill an
empty section, so producing one beside a real example would be noise. Authored
examples and an adjacent file, however, are **both** shown. Both are deliberate
acts by a person, and suppressing a hand-written example page because someone
added a one-line `examples:` entry to the flow file would delete content
silently, which is the failure this project spends most of its rules avoiding.
Redundancy is visible; a missing section is not.

**On validation.** An example flow fragment that no longer parses is worse than
no example, because it is indistinguishable from one that works until someone
types it. The engine is already loaded during a docs build, so a fragment can be
loaded exactly as `dfm validate` would load it. What is *not* done is running
anything: an example is documentation, and a docs build that executes a
simulator has stopped being a docs build.
"""

import contextlib
import io
import os
import shutil
import tempfile
from typing import List, Optional

from .model import ExampleDoc, SrcRef

# Cap on parameters written into a generated snippet. A task with thirty
# parameters does not get a thirty-line "minimal" example -- that is neither
# minimal nor an example.
MAX_GENERATED_PARAMS = 6


def adjacent_path(examples_dir: str, name: str, suffix: str = ".rst"):
    """`<examples_dir>/<task>.rst`, by qualified name then by leaf.

    Qualified first so two packages documented in one doc set cannot collide,
    the leaf second because `library.Compile.rst` is a tedious filename for a
    doc set covering one package.
    """
    if not examples_dir:
        return None
    for candidate in (name, name.split('.')[-1]):
        path = os.path.join(examples_dir, candidate + suffix)
        if os.path.exists(path):
            return path
    return None


def _is_placeholder(value) -> bool:
    """Whether a default is the engine's stand-in rather than a real value.

    There are no required parameters (PLAN.md U10): the engine substitutes a
    type default at load, so "declared without a value" is erased before
    anything can read it. An empty default is what survives of that intent --
    the author supplied nothing useful and left it to the caller -- which makes
    it the best available guess at what a minimal example must fill in. It is a
    guess, which is why the result is labelled as generated.
    """
    return value is None or value == "" or value == [] or value == {}


def generate(doc) -> Optional[ExampleDoc]:
    """A minimal snippet synthesized from the declaration.

    For a runnable task, the command line. For everything else, the `uses:`
    stanza that puts it in a flow. Returns None when there is nothing useful to
    synthesize -- an empty code block is worse than an absent section.
    """
    if doc.kind == 'root':
        code = "dfm run %s" % doc.name
        return ExampleDoc(
            title="Run it",
            code=code,
            lang="shell",
            origin="generated",
            caption="Synthesized from the declaration.")

    if doc.kind in ('library', 'compound', 'abstract', 'variants'):
        lines = ["tasks:", "- name: my-%s" % doc.name.split('.')[-1].lower(),
                 "  uses: %s" % doc.name]

        fill = [p for p in doc.params if _is_placeholder(p.default)]
        if fill:
            lines.append("  with:")
            for param in fill[:MAX_GENERATED_PARAMS]:
                lines.append("    %s: # %s" % (param.name, param.type))

        return ExampleDoc(
            title="Use it in a flow",
            code="\n".join(lines),
            lang="yaml",
            origin="generated",
            caption="Synthesized from the declaration: the parameters shown "
                    "are the ones with no default.")

    return None


def is_flow_fragment(code: str) -> bool:
    """Whether `code` is something the engine could load.

    A top-level `package:` or `fragment:` key, which is what makes a snippet a
    file rather than an excerpt. An excerpt cannot be validated -- there is no
    honest way to guess the surrounding file -- so it is left unchecked rather
    than wrapped in a synthesized package that would validate something the
    author never wrote.
    """
    try:
        import yaml
        data = yaml.safe_load(code)
    except Exception:
        return False
    return isinstance(data, dict) and bool(
        {'package', 'fragment'} & set(data.keys()))


def validate(example: ExampleDoc, basedir: Optional[str] = None) -> ExampleDoc:
    """Load a flow-fragment example, recording whether the engine accepted it.

    Mutates and returns `example`. Non-fragments are left with `valid is None`:
    "not checked" and "checked and fine" are different claims, and only one of
    them is worth making on a page.

    A `fragment:` is wrapped in a minimal package, because a fragment is by
    definition not loadable on its own -- that is what makes it a fragment, and
    refusing to check any of them would exempt the most common example shape.
    """
    if example.origin == 'generated' or not is_flow_fragment(example.code):
        return example

    from .loader import load_project

    tmp = tempfile.mkdtemp(prefix="dvflow-doc-example-")
    try:
        _write_project(example.code, tmp)
        with _quiet():
            result = load_project(tmp)
        errors = [m for m in result.markers if m.is_error]
        if result.ok and not errors:
            example.valid = True
            example.error = ""
        else:
            example.valid = False
            example.error = (errors[0].msg if errors
                             else "the engine could not load this example")
    except Exception as e:
        # Validation is a service, not a gate on extraction: a failure to even
        # attempt the check must not lose the example.
        example.valid = None
        example.error = str(e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return example


@contextlib.contextmanager
def _quiet():
    """Swallow whatever the engine prints while loading an example.

    The engine reports some resolution failures on stdout as well as through
    markers. That is fine when a person ran `dfm`; during a docs build it puts
    a bare line with no location into the middle of the build output, and the
    same message is already captured in `ExampleDoc.error` where it belongs.
    """
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        yield


def _write_project(code: str, tmp: str):
    """Lay an example out on disk the way the engine expects to find it."""
    if code.lstrip().startswith('fragment:'):
        with open(os.path.join(tmp, "example.yaml"), "w") as fp:
            fp.write(code)
        code = ("package:\n  name: example\n  fragments:\n"
                "  - example.yaml\n")
    with open(os.path.join(tmp, "flow.yaml"), "w") as fp:
        fp.write(code)


def diagram_model(example: ExampleDoc):
    """The flow diagram of an example, or None (design §9).

    The point of drawing this rather than accepting a hand-made picture: it is
    provably a picture of the code above it. A diagram that drifted two
    releases ago is the exact failure this whole project exists to prevent, and
    an example is where hand-drawn pictures usually live.

    The subject is the first task with a body, falling back to the first task
    declared. Not a heuristic worth agonizing over -- an example small enough
    to be an example rarely has two candidates, and where it does, the one the
    author wrote first is the one the example is about.
    """
    if example.valid is not True:
        return None

    from .diagram import flow
    from .loader import load_project

    tmp = tempfile.mkdtemp(prefix="dvflow-doc-example-")
    try:
        _write_project(example.code, tmp)
        with _quiet():
            result = load_project(tmp)
        if not result.ok:
            return None

        tasks = list((getattr(result.pkg, 'task_m', None) or {}).values())
        if not tasks:
            return None
        subject = next((t for t in tasks if getattr(t, 'subtasks', None)),
                       tasks[0])

        model = flow.build(subject)
        return None if model.is_empty() else model
    except Exception:
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def collect(doc, examples_dir=None, generate_missing=True,
            validate_flow=False) -> List[ExampleDoc]:
    """Every example for `doc`, from all three sources.

    The adjacent file is returned with its **path** in `code` and `origin`
    'file': its contents are reStructuredText, which extraction has no business
    parsing. The renderer includes it. That keeps this module's output plain
    data and keeps rst handling where the rst machinery already is.
    """
    out = list(doc.examples)

    if validate_flow:
        for example in out:
            validate(example)

    path = adjacent_path(examples_dir, doc.name) if examples_dir else None
    if path:
        out.append(ExampleDoc(
            title=None, code=path, lang="rst", origin="file",
            srcinfo=SrcRef(file=path, line=0)))

    if not out and generate_missing:
        generated = generate(doc)
        if generated is not None:
            out.append(generated)

    return out

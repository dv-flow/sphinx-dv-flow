"""The parts of an example that are not just its code (design §9).

Three renderings, each answering a question the code alone leaves open: where
did this come from, does it still load, and what does it build.
"""

import os

from docutils import nodes

from .docfield import parse_doc


def include_file(example, state):
    """An adjacent `.rst`, parsed in place.

    Included rather than linked: an example a reader has to click through to is
    an example most readers will not read. The file's own headings and
    directives work, because this goes through the same nested parse everything
    else does.
    """
    try:
        with open(example.code) as fp:
            text = fp.read()
    except OSError as e:
        from sphinx.util import logging
        logging.getLogger(__name__).warning(
            "could not read example file %s: %s", example.code, e,
            type='dvflow', subtype='examples')
        return []

    return parse_doc(text, state, source=example.code, line=0)


def validity(example):
    """What validation found, when it found something worth saying.

    Only failure is reported. A green "this example loads" badge on every
    snippet is noise proportional to the size of the doc set -- validation's
    value is that a broken example stops being indistinguishable from a working
    one, and that is served entirely by saying so when it breaks.
    """
    if example.valid is not False:
        return []

    node = nodes.warning()
    para = nodes.paragraph()
    para += nodes.strong(text="This example no longer loads. ")
    para += nodes.Text(example.error or "The engine rejected it.")
    node += para
    return [node]


def diagram(example):
    """The example's own flow diagram, when it has one.

    Provably a picture of the code above it -- which is the entire argument for
    generating it rather than accepting a hand-drawn one that drifted two
    releases ago.
    """
    model = getattr(example, '_diagram', None)
    if model is None or model.is_empty():
        return []

    from . import diagrams as render_diagrams
    return render_diagrams.render_model(model)


def prepare(doc, env, base_dir=None):
    """Fill `doc.examples` from all three sources, per the build's settings.

    Called by the directives rather than by extraction: which sources are
    consulted is a documentation-set decision, and the examples directory is a
    path in the Sphinx tree that `dv_flow.doc` has no business knowing about.
    """
    from dv_flow.doc.examples import collect, diagram_model

    config = env.config
    examples_dir = config.dvflow_examples_dir
    if examples_dir and not os.path.isabs(examples_dir):
        examples_dir = os.path.join(str(env.srcdir), examples_dir)

    doc.examples = collect(
        doc,
        examples_dir=examples_dir,
        generate_missing=config.dvflow_examples_generate,
        validate_flow=config.dvflow_examples_validate)

    for example in doc.examples:
        if example.origin == 'file':
            # Registered so editing an example page rebuilds the task page that
            # includes it. Without this the include is invisible to Sphinx and
            # the stale copy survives every incremental build.
            try:
                env.note_dependency(example.code)
            except Exception:
                pass
        elif config.dvflow_examples_diagrams:
            # Stashed on the document rather than added to the extraction
            # contract: a diagram model is a rendering concern, and putting it
            # in the JSON would make `dvflow-doc dump` build pictures.
            example._diagram = diagram_model(example)

    return doc


def report(doc, logger, location=None):
    """Warn about examples the engine refused.

    Warned rather than merely rendered, because the page is read by someone
    looking for an example and the *build* is watched by whoever can fix it.
    Under `-W` this fails the build, which is the point: a broken example is a
    documentation defect with a known location.
    """
    for example in doc.examples:
        if example.valid is False:
            src = example.srcinfo
            where = None
            if src is not None and src.file:
                where = ("%s:%d" % (src.file, src.line) if src.line
                         else src.file)
            logger.warning(
                "example for %s no longer loads: %s", doc.name,
                example.error or "the engine rejected it",
                location=where or location,
                type='dvflow', subtype='examples')

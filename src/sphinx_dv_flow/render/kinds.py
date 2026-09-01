"""Assembling the blocks into a page, per documentation kind (design §4).

The kinds differ in *order and emphasis*, not in content. A root task answers
"how do I run this"; a library task answers "what do I get if I use this". The
same facts appear on both where both audiences need them -- dataflow is
prominent on a library page and demoted on a root page, rather than being
present on one and absent from the other.
"""

from . import blocks, options, params


def render(doc, state, base_dir=None, show_source=True, diagram=None,
           lattice=None):
    """Body nodes for `doc`, chosen by its kind.

    `diagram` and `lattice` are prebuilt, supplied by the directive when the
    task has one. Passed in rather than built here because building them needs
    the loaded project, and this layer deliberately sees only the extraction
    document.
    """
    renderer = {
        'root': _root,
        'library': _library,
        'abstract': _abstract,
        'compound': _compound,
        'variants': _variants,
    }.get(doc.kind, _library)

    out = []
    out += blocks.header(doc)
    # Before the description: a reader who stops early is exactly the reader
    # who most needs to know the task is deprecated.
    out += blocks.lifecycle(doc)
    out += (renderer(doc, state, base_dir, lattice)
            if renderer is _variants else renderer(doc, state, base_dir))

    if diagram is not None and not diagram.is_empty():
        from . import diagrams as render_diagrams
        out.append(blocks.section_title("Sub-flow", "body", state))
        out += render_diagrams.render_model(diagram)

    if show_source:
        out += blocks.source(doc, base_dir)
    return out


def _root(doc, state, base_dir):
    """The command-line interface view."""
    out = []

    out += options.synopsis(doc)
    out += blocks.description(doc, state)

    opts = options.option_list(doc)
    if opts:
        out.append(blocks.section_title("Options"))
        out += opts

    define_only = options.define_only_params(doc)
    if define_only:
        out.append(blocks.section_title("Other parameters"))
        # Said once, here, rather than repeated per row.
        note = blocks.nodes.paragraph()
        note += blocks.nodes.Text(
            "These have no flag of their own. Set them with ")
        note += blocks.nodes.literal(text="-D")
        note += blocks.nodes.Text(".")
        out.append(note)
        out += define_only

    out += blocks.examples(doc, state)

    # Demoted, and only when the author actually said something: someone
    # running a task cares what files appear, not what item types flow
    # (design §4.1). An undeclared `consumes` with no `produces` is not a
    # contract, and a section reporting one is noise on a page about a command.
    if doc.consumes_declared or doc.produces:
        out.append(blocks.section_title("Dataflow"))
        out += blocks.dataflow(doc, state)

    # A root+export task gets the library view too -- both audiences are real,
    # and the second one is invisible if classification is allowed to swallow it.
    if 'also-library' in doc.facets:
        out.append(blocks.section_title("Using this task in a flow"))
        out += blocks.signature(doc)
        out += params.param_table(doc)
        out += params.value_docs(doc)
        out += blocks.needs(doc, state)
        out += blocks.facts(doc, state)

    return out


def _library(doc, state, base_dir):
    """The composable building block view."""
    out = []

    out += blocks.signature(doc)
    out += blocks.description(doc, state)

    if doc.params:
        out.append(blocks.section_title("Parameters", "with", state))
        out += params.param_table(doc)
        out += params.value_docs(doc)

    out.append(blocks.section_title("Dataflow"))
    out += blocks.dataflow(doc, state)
    out += blocks.needs(doc, state)

    out += blocks.examples(doc, state)

    facts = blocks.facts(doc, state)
    if facts:
        out.append(blocks.section_title("Behavior"))
        out += facts

    return out


def _abstract(doc, state, base_dir):
    """The extension-point view (design §4.3).

    A reader arrives at an abstract task asking "how do I derive from this",
    which is neither of the questions the other two kinds answer. Three things
    follow from that:

    - **no synopsis, ever.** Even when the task declares `scope: root`, it
      cannot be run, and offering a command line would be an invitation to an
      error the page itself caused. Extraction already withholds `usage` for
      this kind; not calling the options renderer is the second half.
    - **parameters split by obligation.** "You must set this" and "you may
      change this" are different instructions, and a single table makes the
      reader work out which is which from the defaults.
    - **known implementations**, which nothing in the flow file answers --
      `uses:` points the other way, so the reverse index supplies it.
    """
    out = []

    banner = blocks.nodes.note()
    para = blocks.nodes.paragraph()
    para += blocks.nodes.strong(text="Abstract. ")
    para += blocks.nodes.Text(
        "This task cannot be run or referenced directly. Derive from it with ")
    para += blocks.nodes.literal(text="uses:")
    para += blocks.nodes.Text(".")
    banner += para
    out.append(banner)

    out += blocks.signature(doc)
    out += blocks.description(doc, state)

    must, may = _split_by_obligation(doc)

    if must:
        out.append(blocks.section_title("Parameters an implementation must set"))
        out += params.param_table(_with_params(doc, must))
    if may:
        out.append(blocks.section_title("Parameters an implementation may override"))
        out += params.param_table(_with_params(doc, may))
    out += params.value_docs(doc)

    if doc.requires:
        out.append(blocks.section_title("Contract", "requires", state))
        para = blocks.nodes.paragraph()
        para += blocks.nodes.Text(
            "Anything deriving from this task must satisfy:")
        out.append(para)
        bullet = blocks.nodes.bullet_list()
        for req in doc.requires:
            item = blocks.nodes.list_item()
            entry = blocks.nodes.paragraph()
            entry += blocks._type_xref(req.name)
            set_params = ["%s=%s" % (k, v) for k, v in (req.params or {}).items()
                          if v not in (None, "", [], {})]
            if set_params:
                entry += blocks.nodes.Text(" ")
                entry += blocks.nodes.literal(text=", ".join(set_params))
            item += entry
            bullet += item
        out.append(bullet)

    if doc.implementations:
        out.append(blocks.section_title("Known implementations"))
        bullet = blocks.nodes.bullet_list()
        for name in doc.implementations:
            item = blocks.nodes.list_item()
            para = blocks.nodes.paragraph()
            para += blocks._task_xref(name)
            item += para
            bullet += item
        out.append(bullet)
    else:
        # Absence is informative here: an extension point nothing extends is
        # either new or dead, and either way the reader should not conclude the
        # page is unfinished.
        para = blocks.nodes.paragraph()
        para += blocks.nodes.emphasis(
            text="Nothing in this package derives from this task.")
        out.append(para)

    out += blocks.dataflow(doc, state)
    out += blocks.examples(doc, state)

    return out


def _split_by_obligation(doc):
    """`(must-set, may-override)`.

    A parameter counts as "must set" when its default is the type's empty value
    and the task declared it -- an empty string is not a usable tool name, it is
    the absence of one. This is a heuristic, and it is stated as an obligation
    rather than enforced because the engine has no required-parameter concept
    (see PLAN.md U10); getting it wrong costs a parameter appearing under the
    wrong heading, not a wrong fact.
    """
    must, may = [], []
    for param in doc.params:
        if param.inherited:
            may.append(param)
        elif param.default in (None, "", [], {}):
            must.append(param)
        else:
            may.append(param)
    return must, may


def _with_params(doc, subset):
    import copy
    clone = copy.copy(doc)
    clone.params = subset
    return clone


def _compound(doc, state, base_dir):
    """The sub-flow view (design §4.4).

    A compound's body is what it is FOR, so the diagram is the centrepiece and
    the directive supplies it. Everything else is the library view: a compound
    is still something you `uses:` or `needs:`, and its parameters and dataflow
    contract matter to whoever does.
    """
    return _library(doc, state, base_dir)


def _variants(doc, state, base_dir, lattice=None):
    """The addressable-cells view (design §4.5).

    A family is a catalog, not a task with options: each cell is a task in its
    own right, named `<family>.<key>`, and the thing a reader needs is the list
    of names they can actually type. The lattice IS the content here, so it
    comes before everything except the description.
    """
    from . import lattice as render_lattice

    out = []
    out += blocks.description(doc, state)

    if lattice is not None:
        out.append(blocks.section_title("Variants", "strategy", state))
        out += render_lattice.render(lattice)

    if doc.params:
        out.append(blocks.section_title("Parameters", "with", state))
        out += params.param_table(doc)
        out += params.value_docs(doc)

    out += blocks.dataflow(doc, state)
    out += blocks.needs(doc, state)
    out += blocks.examples(doc, state)
    return out

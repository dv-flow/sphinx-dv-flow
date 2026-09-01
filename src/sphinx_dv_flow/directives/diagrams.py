"""The diagram directives: flow, inheritance, dataflow, package, elaborated."""

from docutils import nodes
from docutils.parsers.rst import directives

from ..render import diagrams as render_diagrams
from .auto import _DvfAutoBase, _bool_option


def _int_option(argument):
    return int(argument.strip())


class DvfFlowDiagram(_DvfAutoBase):
    """The declared sub-flow of a compound task (design §6.2).

    Declared, not elaborated: the body is drawn as written, with a `matrix:`
    rendered once inside a labelled region rather than expanded into one box
    per combination. Smaller, truer to the flow file, and identical on every
    machine.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
        'depth': _int_option,
        'max-nodes': _int_option,
        'no-dataflow': directives.flag,
        'no-twin': directives.flag,
    }

    def run(self):
        from dv_flow.doc.diagram import flow
        from dv_flow.doc.loader import find_task

        name = self.arguments[0].strip()
        root, result = self._load()
        if not result.ok:
            return [self._error("could not load flow project at %s" % root)]

        task = find_task(result.pkg, name)
        if task is None:
            return [self._error(
                "no task named '%s' in flow project at %s" % (name, root))]

        model = flow.build(
            task,
            depth=self.options.get(
                'depth', self.env.config.dvflow_diagram_depth),
            max_nodes=self.options.get(
                'max-nodes', self.env.config.dvflow_diagram_max_nodes),
            # An inferred dataflow edge is useful and is still an inference.
            # Turning it off is offered because a reader who wants only what
            # the author declared should be able to have exactly that.
            dataflow=('no-dataflow' not in self.options
                      and self.env.config.dvflow_diagram_dataflow))

        if model.is_empty():
            return [self._error(
                "task '%s' has no declared body to draw" % task.name)]

        return render_diagrams.render_model(
            model, twin=('no-twin' not in self.options))


class DvfInheritance(_DvfAutoBase):
    """The `uses:` hierarchy as a UML class diagram (design §6.4)."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
        'descendants': _bool_option,
        'max-descendants': _int_option,
        'no-twin': directives.flag,
    }

    def run(self):
        from dv_flow.doc.diagram import inherit
        from dv_flow.doc.indices import build_index
        from dv_flow.doc.loader import find_task

        name = self.arguments[0].strip()
        root, result = self._load()
        if not result.ok:
            return [self._error("could not load flow project at %s" % root)]

        index = build_index(result.pkg)

        task = find_task(result.pkg, name)
        if task is not None:
            model = inherit.build(
                task, index=index,
                descendants=self.options.get('descendants', False),
                max_descendants=self.options.get(
                    'max-descendants', inherit.DEFAULT_MAX_DESCENDANTS))
        else:
            from .auto import _find_type
            tt = _find_type(result.pkg, name)
            if tt is None:
                return [self._error(
                    "no task or type named '%s' in flow project at %s"
                    % (name, root))]
            model = inherit.build_for_type(tt, index)

        if model.is_empty():
            # A single box is not a diagram. It repeats the heading and tells
            # the reader nothing, so say why nothing was drawn instead.
            return [self._error(
                "'%s' has no inheritance relationships to draw" % name)]

        return render_diagrams.render_model(
            model, twin=('no-twin' not in self.options))


class DvfDataflow(_DvfAutoBase):
    """The producer → type → consumer map (design §6.5).

    With an argument, the map centred on one type. Without one, the map over
    the whole package -- which is the closest thing to "what can I plug into
    what" that a flow library has, and the most likely centrepiece for a
    package with no runnable tasks at all.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = False
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
        'internal': _bool_option,
        'max-nodes': _int_option,
        'no-twin': directives.flag,
    }

    def run(self):
        from dv_flow.doc.diagram import dataflow
        from dv_flow.doc.indices import build_index
        from dv_flow.doc.package import documented_tasks

        root, result = self._load()
        if not result.ok:
            return [self._error("could not load flow project at %s" % root)]

        index = build_index(result.pkg)
        max_nodes = self.options.get('max-nodes', dataflow.DEFAULT_MAX_NODES)

        if self.arguments:
            model = dataflow.build_for_type(
                self.arguments[0].strip(), index, max_nodes=max_nodes)
        else:
            # Limited to documented tasks: a map routing through an internal
            # task tells the reader to use something they cannot name.
            model = dataflow.build_for_package(
                result.pkg, index,
                documented=documented_tasks(
                    result.pkg,
                    internal=self.options.get(
                        'internal', self.env.config.dvflow_internal)),
                max_nodes=max_nodes)

        if model.is_empty():
            return [self._error(
                "nothing produces or consumes anything in %s" % root)]

        return render_diagrams.render_model(
            model, twin=('no-twin' not in self.options))


class DvfPackageDiagram(_DvfAutoBase):
    """The component view: provided and required interfaces (design §6.6)."""

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
        'internal': _bool_option,
        'no-twin': directives.flag,
    }

    def run(self):
        from dv_flow.doc.diagram import package as package_diagram
        from dv_flow.doc.indices import build_index
        from dv_flow.doc.package import documented_tasks, extract_package

        root, result = self._load()
        if not result.ok:
            return [self._error("could not load flow project at %s" % root)]

        internal = self.options.get('internal', self.env.config.dvflow_internal)
        index = build_index(result.pkg)
        model = package_diagram.build(
            result.pkg, index,
            doc=extract_package(result.pkg, internal=internal),
            documented=documented_tasks(result.pkg, internal=internal))

        if model.is_empty():
            return [self._error(
                "package at %s has no interfaces or imports to draw" % root)]

        return render_diagrams.render_model(
            model, twin=('no-twin' not in self.options))


class DvfElaborated(_DvfAutoBase):
    """The instance graph, as the engine will actually build it (§6.1).

    Opt-in, always. An elaborated graph is one machine's expansion of one
    configuration -- a different `-D`, a different environment, and it is a
    different picture. So it is never a default, and it is rendered with the
    parameters it was built under so nobody mistakes an expansion for the
    definition.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
    }

    def run(self):
        from docutils import nodes as docnodes

        from dv_flow.doc.diagram import elaborated
        from dv_flow.doc.loader import find_task

        name = self.arguments[0].strip()
        root, result = self._load()
        if not result.ok:
            return [self._error("could not load flow project at %s" % root)]

        task = find_task(result.pkg, name)
        if task is None:
            return [self._error(
                "no task named '%s' in flow project at %s" % (name, root))]

        built = elaborated.build(task, result.pkg, result.loader)
        if not built.ok:
            # Elaboration touches the filesystem and the environment, so it can
            # fail for reasons unrelated to the flow file being wrong. Ground
            # rule §0.4: say so on the page and carry on.
            return [self._error(
                "could not elaborate '%s' here: %s" % (name, built.error))]

        out = []

        note = docnodes.note()
        para = docnodes.paragraph()
        para += docnodes.strong(text="Elaborated view. ")
        para += docnodes.Text(
            "This is one expansion of this task, under the parameters below. "
            "It is not the definition, and another environment may expand it "
            "differently.")
        note += para
        if built.params:
            items = docnodes.definition_list()
            for key in sorted(built.params):
                item = docnodes.definition_list_item()
                term = docnodes.term()
                term += docnodes.literal(text=key)
                item += term
                definition = docnodes.definition()
                definition += docnodes.paragraph(text=built.params[key])
                item += definition
                items += item
            note += items
        out.append(note)

        block = docnodes.literal_block(built.dot, built.dot)
        block['language'] = 'text'
        block['classes'] = ['dvf-diagram', 'dvf-elaborated']
        try:
            from sphinx.ext.graphviz import graphviz
            node = graphviz()
            node['code'] = built.dot
            node['options'] = {'docname': ''}
            out.append(node)
        except ImportError:
            out.append(block)

        return out

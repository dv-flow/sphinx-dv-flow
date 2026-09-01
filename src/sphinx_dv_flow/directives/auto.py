"""``dvf:autotask``, ``dvf:autotype`` and ``dvf:autopackage``.

The failure mode these are written against: a docs build that dies because one
task in one package referenced something the documentation environment cannot
resolve. Ground rule §0.4 -- degrade to declared text and warn; fail only on a
malformed flow file, which is a real error with a real location.
"""

import os

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

from ..config import project_root
from ..domain import anchor_for
from ..env import load, note_dependencies
from ..render import kinds
from ..render import types as render_types


def _bool_option(argument):
    """A flag option that may also be given a value.

    `:internal:` and `:internal: true` should mean the same thing; so should
    `:internal: false` meaning off. `directives.flag` handles only the first.
    """
    if argument is None or not argument.strip():
        return True
    return argument.strip().lower() not in ('false', 'no', '0', 'off')


def _list_option(argument):
    """A comma- or whitespace-separated list."""
    if not argument:
        return []
    return [part for part in argument.replace(',', ' ').split() if part]


class _DvfAutoBase(SphinxDirective):
    """Shared loading, error reporting and section construction."""

    def _load(self):
        root = project_root(self.env, self.options.get('root'))
        config = self.options.get('config') or self.env.config.dvflow_config
        result = load(self.env, root, config, location=self.get_location())
        if result.ok:
            note_dependencies(self.env, result)
        return root, result

    def _diagram_for(self, task, doc):
        """The sub-flow diagram for a compound task, or None.

        Built for compound tasks by default because a compound's body IS its
        content -- a page describing one without showing its shape has left out
        the part the reader came for. `:no-diagram:` turns it off; `:diagram:`
        asks for one on a task that would not get it automatically.
        """
        if 'no-diagram' in self.options:
            return None
        if doc.kind != 'compound' and 'diagram' not in self.options:
            return None

        from dv_flow.doc.diagram import flow
        model = flow.build(
            task,
            depth=self.env.config.dvflow_diagram_depth,
            max_nodes=self.env.config.dvflow_diagram_max_nodes,
            dataflow=self.env.config.dvflow_diagram_dataflow)
        return None if model.is_empty() else model

    def _lattice_for(self, task, doc):
        """The variant lattice for a `select:` family, or None."""
        if doc.kind != 'variants':
            return None
        from dv_flow.doc.diagram import lattice
        return lattice.build(task)

    def _prepare_examples(self, doc):
        """Fill in adjacent-file and generated examples, and validate them.

        Done here rather than in extraction: which sources are consulted is a
        documentation-set decision, and the examples directory is a path in the
        Sphinx tree that `dv_flow.doc` has no business knowing about.
        """
        from sphinx.util import logging

        from ..render import examples as render_examples

        render_examples.prepare(doc, self.env)
        render_examples.report(doc, logging.getLogger(__name__),
                               location=self.get_location())
        return doc

    def _elsewhere(self, name):
        """Refuse to document what another project documents (design §12.3).

        Two doc sets describing the same object is worse than one: references
        resolve to whichever inventory answers first, and the two copies drift
        independently. The name still *links* -- that is what intersphinx is
        for -- so declining to render it costs the reader nothing.
        """
        from ..config import documented_elsewhere

        if not documented_elsewhere(self.env.config, name):
            return None
        return [self._error(
            "'%s' belongs to a package listed in dvflow_intersphinx_packages, "
            "which declares that another project documents it. Remove it from "
            "that list to document it here." % name)]

    def _show_source(self):
        return ('no-source' not in self.options
                and self.env.config.dvflow_show_source)

    def _error(self, message):
        """A visible failure that does not stop the build.

        The message lands in the rendered page as well as in the build log,
        because a page that silently omits a task looks complete.
        """
        from sphinx.util import logging
        logging.getLogger(__name__).warning(
            "%s", message, location=self.get_location(),
            type='dvflow', subtype=self.name.split(':')[-1])
        node = nodes.error()
        node += nodes.paragraph(text=message)
        return node

    def _note_cells(self, task, doc, anchor):
        """Register a family's cell names, all pointing at the family page.

        A cell is what a reader actually types (`dfm run sim-img.vlt`), so a
        reference to one has to resolve. It does not get a page of its own --
        folding cells into the family is the whole point of the variant kind --
        so every cell resolves to the family's anchor.

        Without this, the names on the lattice are the only place cells appear
        and nothing else in the doc set can link to one.
        """
        if doc.kind != 'variants':
            return
        from dv_flow.doc.diagram.lattice import cell_names
        domain = self.env.get_domain('dvf')
        for cell in cell_names(task):
            domain.note_object('task', cell, self.env.docname, anchor)

    def _section(self, objtype, name, body, noindex=False):
        section = nodes.section()
        section['ids'] = []
        section['names'] = []

        title = nodes.title()
        title += nodes.literal(text=name)
        section += title

        if noindex:
            # `:noindex:` means "do not claim the name in the domain", not "have
            # no anchor". A section with no id at all crashes Sphinx's toctree
            # collector, and an un-linkable heading is not what anyone was
            # asking for -- so docutils assigns a unique one, which also avoids
            # colliding with the indexed copy of the same task elsewhere.
            self.state.document.set_id(section)
        else:
            anchor = anchor_for(objtype, name)
            section['ids'].append(anchor)
            self.env.get_domain('dvf').note_object(
                objtype, name, self.env.docname, anchor)
            self.state.document.note_explicit_target(section)

        section += body
        return section

    def _section_for_task(self, task, doc, body, noindex=False):
        section = self._section('task', doc.name, body, noindex=noindex)
        if not noindex:
            self._note_cells(task, doc, anchor_for('task', doc.name))
        return section


class DvfAutoTask(_DvfAutoBase):
    """Document one task, extracted from the flow project."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
        'no-source': directives.flag,
        'noindex': directives.flag,
        'diagram': directives.flag,
        'no-diagram': directives.flag,
    }

    def run(self):
        name = self.arguments[0].strip()
        elsewhere = self._elsewhere(name)
        if elsewhere is not None:
            return elsewhere

        root, result = self._load()
        if not result.ok:
            # The markers were already reported against the flow file by
            # `load`, which is the location a reader can act on. Repeating them
            # here would point at the .rst instead.
            return [self._error("could not load flow project at %s" % root)]

        from dv_flow.doc.indices import build_index
        from dv_flow.doc.loader import find_task
        from dv_flow.doc.task import extract_task

        task = find_task(result.pkg, name)
        if task is None:
            return [self._error(
                "no task named '%s' in flow project at %s" % (name, root))]

        index = build_index(result.pkg)
        self.env.get_domain('dvf').note_reverse(self.env.docname, index)
        doc = extract_task(task, result.pkg, result.loader, index=index)
        self._prepare_examples(doc)
        body = kinds.render(doc, self.state, base_dir=root,
                            show_source=self._show_source(),
                            diagram=self._diagram_for(task, doc),
                            lattice=self._lattice_for(task, doc))
        return [self._section_for_task(
            task, doc, body, noindex='noindex' in self.options)]


class DvfAutoType(_DvfAutoBase):
    """Document one data type."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
        'no-source': directives.flag,
        'noindex': directives.flag,
        'diagram': directives.flag,
        'no-diagram': directives.flag,
    }

    def run(self):
        name = self.arguments[0].strip()
        root, result = self._load()
        if not result.ok:
            return [self._error("could not load flow project at %s" % root)]

        from dv_flow.doc.indices import apply_to_type, build_index
        from dv_flow.doc.type import extract_type

        tt = _find_type(result.pkg, name)
        if tt is None:
            return [self._error(
                "no type named '%s' in flow project at %s" % (name, root))]

        doc = apply_to_type(extract_type(tt, result.pkg), build_index(result.pkg))
        body = render_types.render(doc, self.state, base_dir=root,
                                   show_source=self._show_source())
        return [self._section('type', doc.name, body,
                              noindex='noindex' in self.options)]


def _find_type(pkg, name):
    """Resolve a type name, accepting the unqualified leaf when unambiguous."""
    type_m = getattr(pkg, 'type_m', {}) or {}
    if name in type_m:
        return type_m[name]
    qualified = "%s.%s" % (getattr(pkg, 'name', ''), name)
    if qualified in type_m:
        return type_m[qualified]
    matches = [t for n, t in type_m.items() if n.split('.')[-1] == name]
    return matches[0] if len(matches) == 1 else None


def _package_map_nodes(result, internal):
    from dv_flow.doc.diagram import dataflow
    from dv_flow.doc.indices import build_index
    from dv_flow.doc.package import documented_tasks

    index = build_index(result.pkg)
    return dataflow.build_for_package(
        result.pkg, index,
        documented=documented_tasks(result.pkg, internal=internal))


class DvfAutoPackage(_DvfAutoBase):
    """Document what a package publishes.

    Visibility drives inclusion: `root` and `export` tasks by default,
    package-internal ones with `:internal:`, and `local` never -- a
    fragment-scoped task is not addressable by a reader whatever the option
    says.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = False
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
        'internal': _bool_option,
        'deprecated': _bool_option,
        'kinds': _list_option,
        'members': _list_option,
        'exclude': _list_option,
        'group-by': directives.unchanged,
        'types': _bool_option,
        'configs': _bool_option,
        'filters': _bool_option,
        'no-source': directives.flag,
        'diagram': directives.flag,
        'no-diagram': directives.flag,
        'map': _bool_option,
    }

    def run(self):
        root, result = self._load()
        if not result.ok:
            node = nodes.error()
            node += nodes.paragraph(
                text="could not load flow project at %s" % root)
            return [node]

        from dv_flow.doc.indices import apply_to_type, build_index
        from dv_flow.doc.package import (KIND_HEADINGS, documented_tasks,
                                         documented_types, group_by_kind)
        from dv_flow.doc.task import extract_task
        from dv_flow.doc.type import extract_type

        elsewhere = self._elsewhere(getattr(result.pkg, 'name', ''))
        if elsewhere is not None:
            return elsewhere

        internal = self.options.get(
            'internal', self.env.config.dvflow_internal)
        # Deprecated tasks are excluded from a listing by default because a
        # listing is a menu -- it answers "what can I use here", and a task
        # nobody should use is a wrong answer. The page still exists when
        # requested by name, so links from old flow files keep working and
        # still show the banner.
        include_deprecated = self.options.get('deprecated', False)
        show_source = self._show_source()
        index = build_index(result.pkg)
        # Recorded so the indices can answer "what produces this type" over
        # every package any document covered.
        self.env.get_domain('dvf').note_reverse(self.env.docname, index)

        tasks = documented_tasks(
            result.pkg,
            internal=internal,
            kinds=self.options.get('kinds'),
            members=self.options.get('members'),
            exclude=self.options.get('exclude'),
            include_deprecated=include_deprecated)

        out = []

        # A package with no runnable tasks is a library, and the question its
        # landing page has to answer first is "what can I plug into what" --
        # not "here is a list of tasks". Where there ARE entry points, they
        # come first: someone who can run something wants to know that before
        # they read a type map.
        if self.options.get('map', not any(
                getattr(t, 'is_root', False) for t in tasks)):
            out += self._package_map(result, root, internal)

        group_by = self.options.get('group-by', 'kind')
        if group_by == 'none':
            groups = [(None, tasks)]
        else:
            groups = group_by_kind(tasks)

        for kind, group in groups:
            if kind is not None and len(groups) > 1:
                # Only when there is more than one group: a heading over the
                # single group on a package with only library tasks is a label
                # for the whole page, which the page already has.
                heading = nodes.paragraph(classes=['dvf-group-title'])
                heading += nodes.strong(
                    text=KIND_HEADINGS.get(kind, kind.title()))
                out.append(heading)

            for task in group:
                doc = extract_task(task, result.pkg, result.loader, index=index)
                self._prepare_examples(doc)
                body = kinds.render(doc, self.state, base_dir=root,
                                    show_source=show_source,
                                    diagram=self._diagram_for(task, doc),
                                    lattice=self._lattice_for(task, doc))
                out.append(self._section_for_task(task, doc, body))

        if self.options.get('types', False):
            for tt in documented_types(result.pkg):
                doc = apply_to_type(extract_type(tt, result.pkg), index)
                body = render_types.render(doc, self.state, base_dir=root,
                                           show_source=show_source)
                out.append(self._section('type', doc.name, body))

        # Filters and configurations follow the tasks, in the §4.7 order, and
        # they appear by DEFAULT where types do not. A type has somewhere else
        # to live -- its own page, the type index, a cross-reference from every
        # `produces:` entry that names it. A configuration has none of those: if
        # the package page does not mention it, a reader has no way to discover
        # that `-c ci` is a thing they may type.
        out += self._filters(result, root, internal, show_source)
        out += self._configs(result, root, show_source)

        return out

    def _configs(self, result, root, show_source):
        from dv_flow.doc.config import documented_configs, extract_config

        from ..render import configs as render_configs
        from .package_objects import _qualified

        if not self.options.get('configs', True):
            return []
        selected = documented_configs(result.pkg)
        if not selected:
            return []

        out = [self._group_heading("Configurations")]
        for cfg in selected:
            doc = extract_config(cfg, result.pkg)
            body = render_configs.render(doc, self.state, base_dir=root,
                                         show_source=show_source)
            out.append(self._section('config', _qualified(doc), body))
        return out

    def _filters(self, result, root, internal, show_source):
        from dv_flow.doc.filter import documented_filters, extract_filter

        from ..render import filters as render_filters
        from .package_objects import _qualified

        if not self.options.get('filters', True):
            return []
        selected = documented_filters(result.pkg, internal=internal)
        if not selected:
            return []

        out = [self._group_heading("Filters")]
        for fd in selected:
            doc = extract_filter(fd, result.pkg)
            body = render_filters.render(doc, self.state, base_dir=root,
                                         show_source=show_source)
            out.append(self._section('filter', _qualified(doc), body))
        return out

    def _group_heading(self, text):
        heading = nodes.paragraph(classes=['dvf-group-title'])
        heading += nodes.strong(text=text)
        return heading

    def _package_map(self, result, root, internal):
        """The package-wide dataflow map, as a landing-page opener."""
        from ..render import diagrams as render_diagrams

        model = _package_map_nodes(result, internal)
        if model.is_empty():
            return []

        heading = nodes.paragraph(classes=['dvf-block-title'])
        heading += nodes.strong(text="What connects to what")
        return [heading] + render_diagrams.render_model(model)

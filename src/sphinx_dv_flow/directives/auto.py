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
    }

    def run(self):
        name = self.arguments[0].strip()
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

        doc = extract_task(task, result.pkg, result.loader,
                           index=build_index(result.pkg))
        body = kinds.render(doc, self.state, base_dir=root,
                            show_source=self._show_source())
        return [self._section('task', doc.name, body,
                              noindex='noindex' in self.options)]


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
        'no-source': directives.flag,
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

        tasks = documented_tasks(
            result.pkg,
            internal=internal,
            kinds=self.options.get('kinds'),
            members=self.options.get('members'),
            exclude=self.options.get('exclude'),
            include_deprecated=include_deprecated)

        out = []

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
                body = kinds.render(doc, self.state, base_dir=root,
                                    show_source=show_source)
                out.append(self._section('task', doc.name, body))

        if self.options.get('types', False):
            for tt in documented_types(result.pkg):
                doc = apply_to_type(extract_type(tt, result.pkg), index)
                body = render_types.render(doc, self.state, base_dir=root,
                                           show_source=show_source)
                out.append(self._section('type', doc.name, body))

        return out

"""``dvf:autoconfig`` and ``dvf:autofilter`` -- the §4.7 package-level objects.

Both are declared on a package rather than inside a task, and both are things a
reader selects or invokes by name. That is what makes them documentable objects
rather than package-page prose: a name someone types is a name something else
should be able to link to.
"""

from docutils import nodes
from docutils.parsers.rst import directives

from .auto import _DvfAutoBase, _bool_option, _list_option


class DvfAutoConfig(_DvfAutoBase):
    """Document one configuration, or every configuration in the package."""

    has_content = False
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = False
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
        'members': _list_option,
        'exclude': _list_option,
        'no-source': directives.flag,
        'noindex': directives.flag,
    }

    def run(self):
        from dv_flow.doc.config import (documented_configs, extract_config,
                                        find_config)

        from ..render import configs as render_configs

        root, result = self._load()
        if not result.ok:
            return [self._error("could not load flow project at %s" % root)]

        if self.arguments:
            name = self.arguments[0].strip()
            cfg = find_config(result.pkg, name)
            if cfg is None:
                return [self._error(
                    "no configuration named '%s' in flow project at %s"
                    % (name, root))]
            selected = [cfg]
        else:
            selected = _filtered(documented_configs(result.pkg),
                                 self.options.get('members'),
                                 self.options.get('exclude'))
            if not selected:
                return [self._error(
                    "no configurations declared in flow project at %s" % root)]

        out = []
        for cfg in selected:
            doc = extract_config(cfg, result.pkg)
            body = render_configs.render(doc, self.state, base_dir=root,
                                         show_source=self._show_source())
            out.append(self._section(
                'config', _qualified(doc), body,
                noindex='noindex' in self.options))
        return out


class DvfAutoFilter(_DvfAutoBase):
    """Document one filter, or every documented filter in the package."""

    has_content = False
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = False
    option_spec = {
        'root': directives.unchanged,
        'config': directives.unchanged,
        'internal': _bool_option,
        'members': _list_option,
        'exclude': _list_option,
        'no-source': directives.flag,
        'noindex': directives.flag,
    }

    def run(self):
        from dv_flow.doc.filter import (documented_filters, extract_filter,
                                        find_filter, is_local)

        from ..render import filters as render_filters

        root, result = self._load()
        if not result.ok:
            return [self._error("could not load flow project at %s" % root)]

        if self.arguments:
            name = self.arguments[0].strip()
            fd = find_filter(result.pkg, name)
            if fd is None:
                return [self._error(
                    "no filter named '%s' in flow project at %s"
                    % (name, root))]
            if is_local(fd):
                # Named explicitly and still refused: a `local` filter is
                # fragment-scoped, so a reader outside the fragment cannot
                # invoke it whatever the directive asks for. Documenting it
                # would publish a call that cannot be written.
                return [self._error(
                    "filter '%s' is local to its fragment and cannot be "
                    "documented" % name)]
            selected = [fd]
        else:
            selected = _filtered(
                documented_filters(
                    result.pkg,
                    internal=self.options.get(
                        'internal', self.env.config.dvflow_internal)),
                self.options.get('members'), self.options.get('exclude'))
            if not selected:
                return [self._error(
                    "no documented filters in flow project at %s" % root)]

        out = []
        for fd in selected:
            doc = extract_filter(fd, result.pkg)
            body = render_filters.render(doc, self.state, base_dir=root,
                                         show_source=self._show_source())
            out.append(self._section(
                'filter', _qualified(doc), body,
                noindex='noindex' in self.options))
        return out


def _qualified(doc):
    """`package.name`, matching how tasks and types are indexed.

    A filter or configuration name is unqualified in its own flow file, but the
    domain inventory spans every package a doc set covers. Two packages each
    declaring a `debug` configuration is entirely ordinary, and unqualified
    names would make one of them shadow the other.
    """
    return "%s.%s" % (doc.package, doc.name) if doc.package else doc.name


def _filtered(items, members, exclude):
    import fnmatch

    def matches(name, patterns):
        return any(fnmatch.fnmatch(name, p) for p in patterns)

    out = []
    for item in items:
        name = getattr(item, 'name', '')
        if members and not matches(name, members):
            continue
        if exclude and matches(name, exclude):
            continue
        out.append(item)
    return out

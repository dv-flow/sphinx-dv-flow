"""Indices that answer real questions (design §13 P2).

An alphabetical list of task names is the index a documentation tool produces
when nobody asked what a reader is actually looking for. The questions worth
answering are the ones a flow library makes hard:

    "I have an ObjFile -- what can take one?"
    "What produces a FileSet of Verilog source?"
    "What is deprecated?"

Those are the reverse directions, which is why `dv_flow.doc.indices` exists.
These classes are the Sphinx surface over it.

Entries respect visibility: an index that lists an internal task tells a reader
to use something they cannot name.
"""

from collections import defaultdict

from sphinx.domains import Index


class _DvfIndex(Index):
    """Shared machinery: group entries and emit them in Sphinx's tuple shape.

    Sphinx wants `[(group, [entry, ...])]`. See `_entry` for the tuple shape.
    """

    def _objects(self):
        return self.domain.data.get('objects', {})

    def _entry(self, name, docname, anchor, extra=""):
        # Sphinx's `IndexEntry` is a 7-tuple:
        # (name, subtype, docname, anchor, extra, qualifier, descr).
        # `subtype` 0 means a normal entry rather than a heading. Getting the
        # arity wrong does not fail at construction -- it fails much later, in
        # the theme template while writing the index page.
        return (name, 0, docname, anchor, extra, "", "")

    def _emit(self, groups):
        content = [(group, sorted(entries, key=lambda e: e[0]))
                   for group, entries in sorted(groups.items())]
        # `True` collapses single-entry groups in the rendered index. A page of
        # one-line groups is harder to scan than the list it replaced.
        return content, True


class TaskIndex(_DvfIndex):
    """Every documented task, grouped by package."""

    name = 'tasks'
    localname = 'DV Flow Task Index'
    shortname = 'tasks'

    def generate(self, docnames=None):
        groups = defaultdict(list)
        for (objtype, name), (docname, anchor) in self._objects().items():
            if objtype != 'task':
                continue
            if docnames and docname not in docnames:
                continue
            package = name.rsplit('.', 1)[0] if '.' in name else ''
            groups[package or '(no package)'].append(
                self._entry(name, docname, anchor))
        return self._emit(groups)


class TypeIndex(_DvfIndex):
    """Every documented data type, grouped by package."""

    name = 'types'
    localname = 'DV Flow Type Index'
    shortname = 'types'

    def generate(self, docnames=None):
        groups = defaultdict(list)
        for (objtype, name), (docname, anchor) in self._objects().items():
            if objtype != 'type':
                continue
            if docnames and docname not in docnames:
                continue
            package = name.rsplit('.', 1)[0] if '.' in name else ''
            groups[package or '(no package)'].append(
                self._entry(name, docname, anchor))
        return self._emit(groups)


class ProducedIndex(_DvfIndex):
    """Tasks grouped by the item type they produce.

    "What makes one of these?" -- the question a reader arrives with when they
    have a consumer and need something to feed it.
    """

    name = 'produced'
    localname = 'DV Flow Tasks by Produced Type'
    shortname = 'produces'

    def generate(self, docnames=None):
        groups = defaultdict(list)
        reverse = self.domain.reverse_data()
        objects = self._objects()

        for type_name, producers in reverse.get('produced_by', {}).items():
            for task_name in producers:
                entry = objects.get(('task', task_name))
                if entry is None:
                    # Not documented: internal, local, or simply not on any
                    # page. Listing it would send a reader somewhere that does
                    # not exist.
                    continue
                docname, anchor = entry
                if docnames and docname not in docnames:
                    continue
                groups[type_name].append(
                    self._entry(task_name, docname, anchor))
        return self._emit(groups)


class ConsumedIndex(_DvfIndex):
    """Tasks grouped by the item type they consume.

    Attribute-qualified requirements are listed with their qualifier rather
    than merged into the bare type: a task wanting
    `{type: FileSet, filetype: verilogSource}` is not an answer to "what takes
    any FileSet", and presenting it as one sends the reader down a path that
    will not connect.
    """

    name = 'consumed'
    localname = 'DV Flow Tasks by Consumed Type'
    shortname = 'consumes'

    def generate(self, docnames=None):
        groups = defaultdict(list)
        reverse = self.domain.reverse_data()
        objects = self._objects()
        qualified = reverse.get('consumed_as', {})

        for type_name, consumers in reverse.get('consumed_by', {}).items():
            for task_name in consumers:
                entry = objects.get(('task', task_name))
                if entry is None:
                    continue
                docname, anchor = entry
                if docnames and docname not in docnames:
                    continue
                qualifier = qualified.get(type_name, {}).get(task_name, "")
                groups[type_name].append(
                    self._entry(task_name, docname, anchor, extra=qualifier))
        return self._emit(groups)


class TagIndex(_DvfIndex):
    """Tasks grouped by the tags they carry.

    Lifecycle is the reason this earns a page: "what is deprecated here" is a
    question a maintainer asks about a library they did not write, and it has
    no other answer short of reading every page.
    """

    name = 'tags'
    localname = 'DV Flow Tasks by Tag'
    shortname = 'tags'

    def generate(self, docnames=None):
        groups = defaultdict(list)
        reverse = self.domain.reverse_data()
        objects = self._objects()

        for tag_name, tasks in reverse.get('tagged_with', {}).items():
            for task_name in tasks:
                entry = objects.get(('task', task_name))
                if entry is None:
                    continue
                docname, anchor = entry
                if docnames and docname not in docnames:
                    continue
                groups[tag_name].append(
                    self._entry(task_name, docname, anchor))
        return self._emit(groups)


ALL_INDICES = (TaskIndex, TypeIndex, ProducedIndex, ConsumedIndex, TagIndex)

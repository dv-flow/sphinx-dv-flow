"""The ``dvf`` domain: what a documented flow object is, and how to link to it.

A domain rather than loose directives, because the thing that makes generated
reference documentation usable is not the pages -- it is that ``:dvf:task:`x```
resolves, that names are indexed, and that a rename shows up as a broken
reference instead of as prose that quietly points nowhere.

M1 registers `task` and `type`. `type` has no directive yet (M2), but the xref
type exists now so that `produces:`/`consumes:` entries can be emitted as
pending references from the start. An unresolved one degrades to literal text;
adding the targets later makes every existing page link up with no change to
what the directives emit.
"""

from docutils import nodes
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode


class DvfXRefRole(XRefRole):
    """Marks a reference as written by an author rather than generated.

    The distinction decides whether an unresolved target warns. An author who
    typed `:dvf:task:`sim`` and got no link has made a mistake worth reporting;
    a generated `type` reference from a `produces:` entry legitimately dangles
    when the doc set covers one package of several, and warning about those
    would produce noise proportional to the size of the flow.

    `warn_dangling` is what routes the warning through Sphinx's own machinery
    instead of ours. That ordering is the point: the reference resolver emits
    `missing-reference` -- which is where **intersphinx** resolves a name into
    another project's inventory -- before it warns about anything. Warning from
    `resolve_xref` instead, as this used to, fires before intersphinx has been
    asked, and reports every legitimate cross-project link as a broken one.
    """

    def __init__(self, **kwargs):
        super().__init__(warn_dangling=True, **kwargs)

    def process_link(self, env, refnode, has_explicit_title, title, target):
        refnode['dvf:authored'] = True
        return super().process_link(env, refnode, has_explicit_title, title,
                                    target)


class DvfDomain(Domain):
    name = 'dvf'
    label = 'DV Flow'

    object_types = {
        'task': ObjType('task', 'task'),
        'type': ObjType('type', 'type'),
        'package': ObjType('package', 'package'),
        'config': ObjType('config', 'config'),
        'filter': ObjType('filter', 'filter'),
    }

    roles = {
        'task': DvfXRefRole(),
        'type': DvfXRefRole(),
        'package': DvfXRefRole(),
        'config': DvfXRefRole(),
        'filter': DvfXRefRole(),
    }

    directives = {}

    initial_data = {
        # (objtype, name) -> (docname, anchor)
        'objects': {},
        # docname -> the reverse-index maps contributed by that document.
        #
        # Kept PER DOCUMENT rather than merged on arrival so `clear_doc` can
        # withdraw a document's contribution. On an incremental build only the
        # changed documents are re-read; a single merged blob would keep
        # entries for tasks that a re-read had since removed, and the indices
        # would list objects with no page.
        'reverse': {},
    }

    @property
    def objects(self):
        return self.data.setdefault('objects', {})

    def note_reverse(self, docname, index):
        """Record the reverse-index maps a document's directives built."""
        self.data.setdefault('reverse', {})[docname] = {
            'produced_by': dict(index.produced_by),
            'consumed_by': dict(index.consumed_by),
            'consumed_as': dict(index.consumed_as),
            'tagged_with': dict(index.tagged_with),
        }

    def reverse_data(self):
        """The union of every document's contribution.

        A union, not a last-writer-wins overwrite: two documents may each
        document part of the same package, and an index built from only the
        last one read would silently omit half the answer.
        """
        merged = {}
        for contribution in self.data.get('reverse', {}).values():
            for key, mapping in contribution.items():
                target = merged.setdefault(key, {})
                for entry, value in mapping.items():
                    if isinstance(value, dict):
                        target.setdefault(entry, {}).update(value)
                    else:
                        existing = target.setdefault(entry, [])
                        for item in value:
                            if item not in existing:
                                existing.append(item)
        return merged

    def note_object(self, objtype, name, docname, anchor):
        key = (objtype, name)
        if key in self.objects and self.objects[key][0] != docname:
            # Two pages claiming the same object make every reference to it a
            # coin flip, so say so rather than picking one silently.
            from sphinx.util import logging
            logging.getLogger(__name__).warning(
                "duplicate dvf:%s description of %s, other instance in %s",
                objtype, name, self.objects[key][0],
                location=docname, type='dvflow', subtype='duplicate')
        self.objects[key] = (docname, anchor)

    def clear_doc(self, docname):
        for key, (doc, _) in list(self.objects.items()):
            if doc == docname:
                del self.objects[key]
        self.data.get('reverse', {}).pop(docname, None)

    def merge_domaindata(self, docnames, otherdata):
        """Required for parallel reads: each worker builds its own inventory.

        Without this, objects described in documents read by a subprocess are
        lost, and every reference to them dangles -- intermittently, depending
        on how work was distributed.
        """
        for key, value in otherdata.get('objects', {}).items():
            if value[0] in docnames:
                self.objects[key] = value
        for docname, contribution in otherdata.get('reverse', {}).items():
            if docname in docnames:
                self.data.setdefault('reverse', {})[docname] = contribution

    def resolve_xref(self, env, fromdocname, builder, typ, target, node,
                     contnode):
        entry = self._lookup(typ, target)
        if entry is None:
            # No warning here: returning None lets the reference resolver try
            # `missing-reference` next, which is where intersphinx resolves the
            # name against another project. See `warn_missing_reference`.
            return None
        docname, anchor = entry
        return make_refnode(builder, fromdocname, docname, anchor, contnode,
                            target)

    def unresolved_message(self, typ, target):
        """The message for a reference nothing could resolve, or None.

        A bare "not found" is a poor diagnostic for a name the author nearly
        got right, so near-misses are offered. Leaf matching being *ambiguous*
        is worth saying out loud for the same reason: the fix is to qualify the
        name, and the message can say which names to choose between.
        """
        candidates = [name for (objtype, name) in self.objects
                      if objtype == typ]
        ambiguous = [c for c in candidates if c.split('.')[-1] == target]

        if len(ambiguous) > 1:
            hint = (". '%s' is ambiguous -- qualify it: %s"
                    % (target, ", ".join(sorted(ambiguous))))
        else:
            import difflib
            close = difflib.get_close_matches(target, candidates, n=3,
                                              cutoff=0.5)
            hint = (". Did you mean %s?" % ", ".join(close)) if close else ""

        return "dvf:%s reference target not found: %s%s" % (typ, target, hint)

    def resolve_any_xref(self, env, fromdocname, builder, target, node,
                         contnode):
        results = []
        for objtype in self.object_types:
            entry = self._lookup(objtype, target)
            if entry is not None:
                docname, anchor = entry
                results.append((
                    'dvf:%s' % objtype,
                    make_refnode(builder, fromdocname, docname, anchor,
                                 contnode, target)))
        return results

    def _lookup(self, objtype, target):
        """Exact name first, then the unqualified leaf.

        Leaf matching is what lets a package's own documentation write
        ``:dvf:task:`sim``` without repeating the package name. It is tried
        second and only when unambiguous, so an exact name can never be
        shadowed, and a leaf shared by two packages resolves to neither rather
        than to whichever was read first.
        """
        entry = self.objects.get((objtype, target))
        if entry is not None:
            return entry

        matches = [v for (t, name), v in self.objects.items()
                   if t == objtype and name.split('.')[-1] == target]
        return matches[0] if len(matches) == 1 else None

    def get_objects(self):
        for (objtype, name), (docname, anchor) in self.objects.items():
            yield (name, name, objtype, docname, anchor, 1)


def anchor_for(objtype, name):
    """The HTML anchor for an object. Stable, because links to it are too."""
    return "dvf-%s-%s" % (objtype, name.replace('.', '-'))


def warn_missing_reference(app, domain, node):
    """`warn-missing-reference` handler.

    Fires only after every resolver -- including intersphinx -- has declined,
    which is what makes a warning from here trustworthy. Returning True
    suppresses Sphinx's own generic message in favour of this one; returning
    None for a reference not worth reporting suppresses nothing, so `nitpicky`
    can still surface it for anyone who wants that.
    """
    if domain is None or domain.name != 'dvf':
        return None

    from .config import documented_elsewhere

    target = node.get('reftarget')

    # Declared as another project's to document. Suppressed outright, and
    # deliberately: this is what replaces a `nitpick_ignore` regex, and it
    # replaces it with something narrower -- a package name rather than a
    # pattern -- and something checkable, since a configured inventory turns
    # the same reference into a link instead.
    if documented_elsewhere(app.config, target):
        return True

    # Generated rather than written. The dataflow blocks emit one reference per
    # produced and consumed item, and those legitimately dangle when the doc set
    # covers one package of several. Returning None rather than True leaves
    # Sphinx's own `nitpicky` reporting intact for anyone who wants it.
    if not node.get('dvf:authored') and not node.get('refexplicit'):
        return None

    from sphinx.util import logging

    message = domain.unresolved_message(node.get('reftype'), target)
    if message is None:
        return None

    logging.getLogger(__name__).warning(
        "%s", message, location=node, type='dvflow', subtype='xref')
    return True

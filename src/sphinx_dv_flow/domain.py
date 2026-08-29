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
    """

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
    }

    roles = {
        'task': DvfXRefRole(),
        'type': DvfXRefRole(),
        'package': DvfXRefRole(),
    }

    directives = {}

    initial_data = {
        # (objtype, name) -> (docname, anchor)
        'objects': {},
    }

    @property
    def objects(self):
        return self.data.setdefault('objects', {})

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

    def merge_domaindata(self, docnames, otherdata):
        """Required for parallel reads: each worker builds its own inventory.

        Without this, objects described in documents read by a subprocess are
        lost, and every reference to them dangles -- intermittently, depending
        on how work was distributed.
        """
        for key, value in otherdata.get('objects', {}).items():
            if value[0] in docnames:
                self.objects[key] = value

    def resolve_xref(self, env, fromdocname, builder, typ, target, node,
                     contnode):
        entry = self._lookup(typ, target)
        if entry is None:
            self._warn_unresolved(typ, target, node)
            return None
        docname, anchor = entry
        return make_refnode(builder, fromdocname, docname, anchor, contnode,
                            target)

    def _warn_unresolved(self, typ, target, node):
        """Warn about a reference an author wrote, with suggestions.

        Only for references written by hand. The dataflow blocks emit `type`
        references for every produced and consumed item, and those legitimately
        dangle when the doc set covers one package of several -- warning about
        them would produce noise proportional to the size of the flow, which is
        how a warning stream stops being read. Sphinx's `nitpicky` mode still
        reports them for anyone who wants that.

        A bare "not found" is a poor diagnostic for a name the author nearly
        got right, so near-misses are offered. That is also why leaf matching
        being *ambiguous* is worth saying out loud: the fix is to qualify the
        name, which the message can suggest.
        """
        if not node.get('refexplicit') and not node.get('dvf:authored'):
            return

        from sphinx.util import logging

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

        logging.getLogger(__name__).warning(
            "dvf:%s reference target not found: %s%s", typ, target, hint,
            location=node, type='dvflow', subtype='xref')

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

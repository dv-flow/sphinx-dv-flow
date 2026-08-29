"""Extracting a data type: the vocabulary `produces`/`consumes` speak.

A type's own declaration is thin -- a name, some fields, maybe a base. Most of
what a reader wants from a type page points the *other* way: who produces this,
who consumes it, what derives from it. None of that is answerable from the type
itself, which is why `indices.py` exists.
"""

from typing import List, Optional

from .model import ParamDoc, SrcRef, TagDoc, TypeDoc
from .params import _type_name
from .task import _srcref, _tag_docs


def _uses_chain(tt) -> List[str]:
    """Base types, nearest first, excluding the type itself."""
    names = []
    seen = set()
    current = getattr(tt, 'uses', None)
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        name = getattr(current, 'name', None)
        if name:
            names.append(name)
        current = getattr(current, 'uses', None)
    return names


def _fields(tt) -> List[ParamDoc]:
    """The type's fields, merged along `uses:` with provenance.

    Types inherit fields the same way tasks inherit parameters, and a reader of
    a derived type has the same question about any given field: is this one
    yours, or did it come from the base?
    """
    definitions = {}
    types = {}
    origin = {}

    chain = []
    seen = set()
    current = tt
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        current = getattr(current, 'uses', None)

    for level in reversed(chain):
        param_defs = getattr(level, 'param_defs', None)
        if param_defs is None:
            continue
        for name, pdef in getattr(param_defs, 'definitions', {}).items():
            prev = definitions.get(name)
            definitions[name] = (pdef.inherit_from(prev)
                                 if prev is not None and hasattr(pdef, 'inherit_from')
                                 else pdef)
            # Reversed walk means the FIRST level to declare a field is the
            # base-most one, which is where it was introduced -- the same
            # origin-based provenance rule tasks use.
            origin.setdefault(name, getattr(level, 'name', ''))
        types.update(getattr(param_defs, 'types', {}))

    out = []
    type_name = getattr(tt, 'name', '')
    for name in sorted(definitions):
        pdef = definitions[name]
        vs = getattr(pdef, 'values', None)
        declared_by = origin.get(name, '')
        out.append(ParamDoc(
            name=name,
            type=_type_name(types.get(name)),
            default=getattr(pdef, 'value', None),
            desc=getattr(pdef, 'desc', None) or "",
            doc=getattr(pdef, 'doc', None) or "",
            declared_by=declared_by,
            inherited=(declared_by != type_name),
            values=[],
            values_open=bool(getattr(vs, 'open', False)) if vs else False,
            # A type field is not a command-line option and is not settable
            # with -D: it is an attribute of an item flowing through the graph.
            # Leaving `define` empty rather than inventing a `-D` form keeps the
            # renderer from offering a way to set it that does not exist.
            define="",
        ))
        if vs is not None:
            from .params import _value_docs
            out[-1].values = _value_docs(vs)
    return out


def extract_type(tt, pkg=None) -> TypeDoc:
    package = getattr(pkg, 'name', '')
    if not package:
        name = getattr(tt, 'name', '')
        package = name.rsplit('.', 1)[0] if '.' in name else ''

    return TypeDoc(
        name=getattr(tt, 'name', ''),
        package=package,
        doc=getattr(tt, 'doc', None) or '',
        srcinfo=_srcref(tt),
        uses_chain=_uses_chain(tt),
        params=_fields(tt),
        # A `check:` makes this type a graph-build contract rather than a data
        # item, which changes what a reader should do with it entirely -- so it
        # is a facet on the document, not a footnote in the prose.
        facets=(['check'] if getattr(tt, 'check', None) else [])
               + (['tag'] if _is_tag(tt) else []),
        tags=_tag_docs(getattr(tt, 'tags', None)),
        check=getattr(tt, 'check', None),
    )


def _is_tag(tt) -> bool:
    """Whether this type is used as a tag -- i.e. derives from `std.Tag`."""
    current = getattr(tt, 'uses', None)
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if getattr(current, 'name', '') == 'std.Tag':
            return True
        current = getattr(current, 'uses', None)
    return False

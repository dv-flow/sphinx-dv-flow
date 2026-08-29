"""Package-level extraction: the landing page, and what belongs on it.

The package document holds names rather than nested documents. That keeps
`dvflow-doc dump <package>` from dragging in every task, and lets a renderer
decide what to inline -- which is a rendering decision, not an extraction one.
"""

import fnmatch
from typing import List, Optional

from .classify import DEFAULT_KINDS, classify, is_documented_by_default
from .lifecycle import read as read_lifecycle
from .loader import iter_tasks, iter_types
from .model import PackageDoc, SrcRef
from .task import _srcref

# The order kinds appear on a package page. Not alphabetical: it is the order a
# reader arrives in. What can I run, what can I build with, what can I extend,
# what is assembled from other things -- and internals last, when shown at all.
KIND_ORDER = ['root', 'library', 'abstract', 'compound', 'variants',
              'internal']

KIND_HEADINGS = {
    'root': 'Runnable tasks',
    'library': 'Library tasks',
    'abstract': 'Extension points',
    'compound': 'Sub-flows',
    'variants': 'Variant families',
    'internal': 'Internal tasks',
}


def documented_tasks(pkg, internal: bool = False,
                     kinds: Optional[List[str]] = None,
                     members: Optional[List[str]] = None,
                     exclude: Optional[List[str]] = None,
                     include_deprecated: bool = True) -> List:
    """The tasks a docs build should include.

    Visibility drives inclusion (design §3): `root` and `export` are documented,
    package-internal tasks only with `internal=True`, and `local` never -- it is
    fragment-scoped, so a reader has no way to address it whatever the option
    says.

    `members` and `exclude` accept glob patterns against both the full name and
    the leaf, because a doc set that wants "everything starting with sim" should
    not have to know whether the author writes qualified names.
    """
    out = []
    for task in iter_tasks(pkg):
        if getattr(task, 'is_local', False):
            continue
        if not (is_documented_by_default(task) or internal):
            continue

        kind = classify(task)
        if kinds is not None and kind not in kinds:
            continue

        name = getattr(task, 'name', '')
        if members and not _matches_any(name, members):
            continue
        if exclude and _matches_any(name, exclude):
            continue

        if not include_deprecated:
            from .task import _tag_docs
            if read_lifecycle(_tag_docs(getattr(task, 'tags', None))).is_deprecated:
                continue

        out.append(task)
    return out


def _matches_any(name, patterns) -> bool:
    leaf = name.split('.')[-1]
    return any(fnmatch.fnmatch(name, p) or fnmatch.fnmatch(leaf, p)
               for p in patterns)


def group_by_kind(tasks):
    """`[(kind, [task])]` in reading order, skipping empty groups.

    Grouping rather than one flat list because the kinds answer different
    questions, and a reader who wants "what can I run" should not have to scan
    past every library task to find out.
    """
    buckets = {}
    for task in tasks:
        buckets.setdefault(classify(task), []).append(task)

    out = []
    for kind in KIND_ORDER:
        if buckets.get(kind):
            out.append((kind, buckets.pop(kind)))
    # Anything the order does not name still gets shown -- silently dropping a
    # task because a new kind was added upstream is the worst failure mode here.
    for kind in sorted(buckets):
        out.append((kind, buckets[kind]))
    return out


def documented_types(pkg, members=None, exclude=None) -> List:
    out = []
    for tt in iter_types(pkg):
        name = getattr(tt, 'name', '')
        if members and not _matches_any(name, members):
            continue
        if exclude and _matches_any(name, exclude):
            continue
        out.append(tt)
    return out


def extract_package(pkg, internal: bool = False, **kw) -> PackageDoc:
    srcinfo = getattr(getattr(pkg, 'pkg_def', None), 'srcinfo', None)
    src = None
    if srcinfo is not None and getattr(srcinfo, 'file', None):
        src = SrcRef(file=srcinfo.file,
                     line=getattr(srcinfo, 'lineno', None)
                     or getattr(srcinfo, 'line', 0) or 0)

    tasks = documented_tasks(pkg, internal=internal, **kw)

    return PackageDoc(
        name=getattr(pkg, 'name', ''),
        desc=getattr(pkg, 'desc', '') or '',
        doc=getattr(pkg, 'doc', '') or '',
        srcinfo=src,
        tasks=[t.name for t in tasks],
        types=[t.name for t in documented_types(pkg)],
        imports=_imports(pkg),
        groups=[(kind, [t.name for t in group])
                for kind, group in group_by_kind(tasks)],
    )


def _imports(pkg) -> List[str]:
    """Packages this one imports, by name.

    Read from the package definition rather than from resolved packages: an
    import that failed to resolve is exactly the one a reader needs to see
    named, and the resolved map would silently omit it.
    """
    pkg_def = getattr(pkg, 'pkg_def', None)
    out = []
    for entry in (getattr(pkg_def, 'imports', None) or []):
        name = getattr(entry, 'name', None)
        if name is None and isinstance(entry, str):
            name = entry
        if name:
            out.append(name)
    return out

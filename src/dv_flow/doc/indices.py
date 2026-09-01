"""Reverse indices: the questions the declarations do not answer.

Every relationship in a flow file points one way. A task says what it produces;
nothing says what produces a type. A task says what it uses; nothing says what
derives from it. Those reverse directions are most of what a reference reader
wants -- "I have an ObjFile, what can take one?" -- so they have to be built.

Built **once per project**, not per page. The cost is a walk over every task;
doing it per directive turns an O(n) build into O(n²) on exactly the doc sets
large enough to care.
"""

import dataclasses as dc
from typing import Dict, List


@dc.dataclass
class ReverseIndex:
    """Who produces, consumes, derives from, and is tagged with what.

    Values are task or type names, in declaration order -- stable, and matching
    the order the package page lists them in, so a reader moving between the two
    sees the same sequence.
    """
    produced_by: Dict[str, List[str]] = dc.field(default_factory=dict)
    consumed_by: Dict[str, List[str]] = dc.field(default_factory=dict)
    # Type name -> types that name it in `uses:`. Direct subtypes only: the
    # transitive closure is reconstructible from these and is rarely what a
    # reader wants first.
    derived_types: Dict[str, List[str]] = dc.field(default_factory=dict)
    # Task name -> tasks that name it in `uses:`. This is "known
    # implementations" on an abstract task's page, which is the single most
    # useful thing an extension point can tell a reader.
    implementations: Dict[str, List[str]] = dc.field(default_factory=dict)
    # Tag type name -> tasks carrying it.
    tagged_with: Dict[str, List[str]] = dc.field(default_factory=dict)
    # Type name -> {consuming task -> the qualifier it asked for}.
    #
    # Keyed by CONSUMER, not just by type. `{type: ObjFile}` and
    # `{type: ObjFile, arch: arm}` are different requirements, and one consumer
    # asking for the qualified form does not make its neighbours picky --
    # labelling every edge into a type with the same qualifier states a
    # constraint the other consumers never declared.
    consumed_as: Dict[str, Dict[str, str]] = dc.field(default_factory=dict)

    def to_dict(self):
        return {f.name: getattr(self, f.name) for f in dc.fields(self)}


def _add(mapping, key, value):
    if not key:
        return
    entries = mapping.setdefault(key, [])
    if value not in entries:
        entries.append(value)


def _entry_type(entry):
    if isinstance(entry, dict):
        return entry.get('type')
    return None


def _entry_text(entry):
    if not isinstance(entry, dict):
        return str(entry)
    return ", ".join("%s=%s" % (k, v) for k, v in entry.items())


def build_index(pkg) -> ReverseIndex:
    """Walk every task and type in `pkg` once, recording the reverse edges."""
    index = ReverseIndex()

    for task in (getattr(pkg, 'task_m', {}) or {}).values():
        name = getattr(task, 'name', '')

        for entry in getattr(task, 'produces', None) or []:
            _add(index.produced_by, _entry_type(entry), name)

        # `consumes` is only a list when it was declared as patterns; the
        # enum forms (All / No) say nothing about a specific type, and
        # recording them would put every task under every type.
        consumes = getattr(task, 'consumes', None)
        if isinstance(consumes, list):
            for entry in consumes:
                type_name = _entry_type(entry)
                _add(index.consumed_by, type_name, name)
                if isinstance(entry, dict) and len(entry) > 1:
                    qualifier = ", ".join(
                        "%s=%s" % (k, v) for k, v in entry.items()
                        if k != 'type')
                    index.consumed_as.setdefault(
                        type_name, {})[name] = qualifier

        base = getattr(task, 'uses', None)
        base_name = getattr(base, 'name', None) if base is not None else None
        # Guard against a Type reached through `uses:` -- legal, but it is not
        # an implementation of a task.
        if base_name and base_name in (getattr(pkg, 'task_m', {}) or {}):
            _add(index.implementations, base_name, name)

        for tag in getattr(task, 'tags', None) or []:
            _add(index.tagged_with, getattr(tag, 'name', None), name)

    for tt in (getattr(pkg, 'type_m', {}) or {}).values():
        base = getattr(tt, 'uses', None)
        base_name = getattr(base, 'name', None) if base is not None else None
        _add(index.derived_types, base_name, getattr(tt, 'name', ''))

    return index


def apply_to_type(doc, index):
    """Fill a `TypeDoc`'s reverse fields. Returns the same document."""
    doc.produced_by = list(index.produced_by.get(doc.name, []))
    doc.consumed_by = list(index.consumed_by.get(doc.name, []))
    doc.derived_by = list(index.derived_types.get(doc.name, []))
    return doc

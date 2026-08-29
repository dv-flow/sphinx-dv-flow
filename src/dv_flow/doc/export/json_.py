"""Canonical JSON for the extraction contract.

"Canonical" is load-bearing: this is what the golden tests compare, so the
output has to be a function of the model and nothing else -- no dict ordering
that depends on hashing, no absolute paths that depend on where the checkout
lives, no floats that render differently on another platform.

Key order follows field-declaration order (see `model._Doc.to_dict`) rather
than being sorted. Sorting would be more obviously canonical, but it would also
scramble the reading order of a document meant to be read by a person running
`dvflow-doc dump`, and declaration order is just as stable.
"""

import json
import os
from typing import Any, Optional


def to_jsonable(doc, base_dir: Optional[str] = None) -> Any:
    """The document as plain data, optionally with paths relativized.

    `base_dir` exists for the golden tests: an absolute `srcinfo.file` changes
    with the checkout location, which would make every golden fail on another
    machine for a reason that has nothing to do with the code.
    """
    data = doc.to_dict() if hasattr(doc, 'to_dict') else doc
    if base_dir is None:
        return data
    return _relativize(data, os.path.abspath(base_dir))


def _relativize(value, base_dir):
    if isinstance(value, dict):
        return {k: _relativize(v, base_dir) for k, v in value.items()}
    if isinstance(value, list):
        return [_relativize(v, base_dir) for v in value]
    if isinstance(value, str) and os.path.isabs(value) and value.startswith(base_dir):
        return os.path.relpath(value, base_dir)
    return value


def dumps(doc, base_dir: Optional[str] = None, indent: int = 2) -> str:
    """JSON text for `doc`.

    `default=str` is a backstop, not a strategy: `_to_jsonable` in the model
    already stringifies anything exotic. It is here so that a field added to
    the contract without a serialization rule degrades to something readable
    instead of raising in the middle of a docs build.
    """
    return json.dumps(to_jsonable(doc, base_dir), indent=indent, default=str)

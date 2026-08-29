"""Interpreting lifecycle tags (design §13 P1).

A lifecycle tag is a claim about **interface churn**, not about runtime
behavior. A `std.Deprecated` task still runs; deprecation is a message to
whoever reads or maintains the flow file.

Two things this module is careful about:

*Absence is not a claim.* An untagged task is assumed stable, and gets no
banner. Inventing a "stable" badge for every untagged task would make the badge
meaningless and bury the tasks that actually said something.

*An empty `replacement` is meaningful.* It says there is no replacement, which
is a different statement from having forgotten to name one -- and the rendering
has to keep them apart, because "use X instead" and "there is nothing to move
to" lead a reader to opposite decisions.
"""

import dataclasses as dc
from typing import List, Optional

DEPRECATED = 'std.Deprecated'
EXPERIMENTAL = 'std.Experimental'
STABLE = 'std.Stable'

# Recognised by leaf name as well as by full name: a project may define its own
# lifecycle tags deriving from these, and a reader does not care which package
# a `Deprecated` came from.
_LEAVES = {
    'Deprecated': DEPRECATED,
    'Experimental': EXPERIMENTAL,
    'Stable': STABLE,
}


@dc.dataclass
class Lifecycle:
    """What a task's lifecycle tags say, as a renderable summary."""
    status: str = 'stable'
    reason: str = ''
    replacement: str = ''
    since: str = ''
    # False when nothing was tagged. `status` is 'stable' either way -- that is
    # the assumed state -- but only a task that SAID so should get a badge.
    declared: bool = False

    @property
    def is_deprecated(self) -> bool:
        return self.status == 'deprecated'

    @property
    def is_experimental(self) -> bool:
        return self.status == 'experimental'

    def to_dict(self):
        return {f.name: getattr(self, f.name) for f in dc.fields(self)}


def _canonical(name):
    if name in _LEAVES.values():
        return name
    return _LEAVES.get(name.split('.')[-1])


def read(tags) -> Lifecycle:
    """The lifecycle a task's tags declare.

    When a task carries more than one, the most cautionary wins:
    deprecated over experimental over stable. A task tagged both `Stable` and
    `Deprecated` is contradictory, and reporting the reassuring half of a
    contradiction is the wrong way to resolve it.
    """
    found = {}
    for tag in tags or []:
        canonical = _canonical(getattr(tag, 'name', '') or '')
        if canonical is None:
            continue
        found[canonical] = getattr(tag, 'params', None) or {}

    for name, status in ((DEPRECATED, 'deprecated'),
                         (EXPERIMENTAL, 'experimental'),
                         (STABLE, 'stable')):
        if name in found:
            params = found[name]
            return Lifecycle(
                status=status,
                reason=params.get('reason', '') or '',
                replacement=params.get('replacement', '') or '',
                since=params.get('since', '') or '',
                declared=True)

    return Lifecycle()


def badge(lifecycle) -> Optional[str]:
    """The short label for the header line, or None when nothing was declared."""
    if not lifecycle.declared:
        return None
    return lifecycle.status


def filter_listing(docs, include_deprecated=False):
    """Drop deprecated entries from a listing unless asked for.

    A listing is a menu: it answers "what can I use here", and a task nobody
    should use any more is a wrong answer to that question. The task's own page
    still exists -- links to it keep working, and someone who arrives from an
    old flow file still gets the banner telling them what to move to.
    """
    if include_deprecated:
        return list(docs)
    return [d for d in docs
            if not read(getattr(d, 'tags', None)).is_deprecated]

"""Documentation coverage (design §10).

The failure mode this exists against is not a wrong page -- it is a page that
was never written and that nobody noticed was missing. A generated doc set
hides that particularly well: every public task gets a heading and a parameter
table whether or not anyone described it, so the output looks complete at
exactly the density where it is emptiest.

So coverage is reported over the **published** surface only. Something a reader
cannot address is not a gap:

- `local` tasks and filters are never counted -- they are not addressable.
- package-internal objects are counted only when `internal=True`, matching what
  the doc set actually publishes.
- a parameter is charged to the task that **introduced** it, not to every task
  that inherits it. Charging inheritors would report one missing sentence N
  times and make the count a measure of inheritance depth.

Sphinx-free, like everything here: the same report backs `dvflow-doc coverage`
and the build-time artifact, so a CI gate and a docs build cannot disagree
about what is undocumented.
"""

import dataclasses as dc
from typing import Any, Dict, List


@dc.dataclass
class Finding:
    """One undocumented thing.

    `owner` is the page it would appear on, `item` the part of that page --
    empty when the object itself is what lacks documentation. Keeping them
    apart is what lets a report group by page, which is how anyone would
    actually go and fix them.
    """
    kind: str = ""
    owner: str = ""
    item: str = ""
    srcfile: str = ""
    srcline: int = 0

    def describe(self) -> str:
        what = "%s %s" % (self.kind, self.owner)
        if self.item:
            what += ", parameter '%s'" % self.item
        return what

    def location(self) -> str:
        if not self.srcfile:
            return ""
        return ("%s:%d" % (self.srcfile, self.srcline)
                if self.srcline else self.srcfile)

    def to_dict(self) -> Dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in dc.fields(self)}


@dc.dataclass
class Report:
    findings: List[Finding] = dc.field(default_factory=list)
    # How many things were examined, by kind. The denominator matters: "12
    # findings" says nothing without it, and a report that only counts failures
    # cannot show progress.
    counted: Dict[str, int] = dc.field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counted.values())

    @property
    def documented(self) -> int:
        return self.total - len(self.findings)

    def percent(self) -> float:
        return 100.0 if not self.total else 100.0 * self.documented / self.total

    def summary(self) -> str:
        return "%d/%d documented (%.0f%%), %d missing" % (
            self.documented, self.total, self.percent(), len(self.findings))

    def by_owner(self) -> List[Any]:
        """`[(owner, [finding])]`, in first-seen order.

        Grouped by page rather than sorted by name: the unit of work for
        someone fixing these is a page, and the order they were found in is the
        order they appear in the flow file.
        """
        groups: Dict[str, List[Finding]] = {}
        for finding in self.findings:
            groups.setdefault(finding.owner, []).append(finding)
        return list(groups.items())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary(),
            "counted": dict(self.counted),
            "documented": self.documented,
            "total": self.total,
            "findings": [f.to_dict() for f in self.findings],
        }


def _undocumented(doc) -> bool:
    """Neither a one-line `desc:` nor prose in `doc:`.

    Either alone is enough. A one-liner is a real answer to "what is this", and
    demanding both would make the report a style check -- which is how a report
    stops being read.
    """
    return not (getattr(doc, 'desc', '') or getattr(doc, 'doc', ''))


def _srcinfo(doc):
    src = getattr(doc, 'srcinfo', None)
    if src is None:
        return "", 0
    return getattr(src, 'file', '') or "", getattr(src, 'line', 0) or 0


def _own_params(doc):
    """Parameters this object introduced.

    An inherited parameter is documented on the task that declared it, and
    that is where the fix belongs. Reporting it against every inheritor turns
    one missing sentence into N findings.
    """
    for param in getattr(doc, 'params', None) or []:
        if getattr(param, 'inherited', False) and param.declared_by != doc.name:
            continue
        yield param


def build(pkg, loader=None, internal: bool = False) -> Report:
    """The coverage report for one loaded package."""
    from .config import documented_configs, extract_config
    from .filter import documented_filters, extract_filter
    from .package import documented_tasks, documented_types
    from .task import extract_task
    from .type import extract_type

    report = Report()

    def examine(kind, doc, with_params=True):
        report.counted[kind] = report.counted.get(kind, 0) + 1
        srcfile, srcline = _srcinfo(doc)
        if _undocumented(doc):
            report.findings.append(Finding(
                kind=kind, owner=doc.name, srcfile=srcfile, srcline=srcline))
        if not with_params:
            return
        for param in _own_params(doc):
            report.counted['parameter'] = report.counted.get('parameter', 0) + 1
            if _undocumented(param):
                report.findings.append(Finding(
                    kind=kind, owner=doc.name, item=param.name,
                    srcfile=srcfile, srcline=srcline))

    for task in documented_tasks(pkg, internal=internal):
        examine('task', extract_task(task, pkg, loader))

    for tt in documented_types(pkg):
        examine('type', extract_type(tt, pkg))

    for cfg in documented_configs(pkg):
        examine('config', extract_config(cfg, pkg), with_params=False)

    for fd in documented_filters(pkg, internal=internal):
        examine('filter', extract_filter(fd, pkg))

    return report


def format_text(report: Report, base_dir=None) -> str:
    """The report as plain text, grouped by page.

    Plain text because this is read in a terminal and in a CI log at least as
    often as on a page, and because it has to be diffable: a coverage report
    whose ordering wobbles cannot be used as a gate.
    """
    import os

    lines = ["Documentation coverage: " + report.summary()]

    if not report.findings:
        lines.append("")
        lines.append("Every published object carries a description.")
        return "\n".join(lines) + "\n"

    for owner, findings in report.by_owner():
        lines.append("")
        location = findings[0].location()
        if location and base_dir:
            try:
                path, _, line = location.partition(':')
                location = os.path.relpath(path, base_dir) + (
                    ':' + line if line else '')
            except ValueError:
                pass
        header = "%s %s" % (findings[0].kind, owner)
        lines.append(header + ("  (%s)" % location if location else ""))
        for finding in findings:
            if finding.item:
                lines.append("    parameter '%s' has no desc: or doc:"
                             % finding.item)
            else:
                lines.append("    no desc: or doc:")

    return "\n".join(lines) + "\n"

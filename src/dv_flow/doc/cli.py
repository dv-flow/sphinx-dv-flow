"""``dvflow-doc`` -- the extractor, without Sphinx in the way.

The subcommands here exist so the extraction contract can be inspected, diffed
and tested as data. ``dump`` in particular is what golden tests compare against,
which means the JSON it emits is a real interface: if a Sphinx directive shows
a fact, this command can print it.

``dump`` is live as of M1. ``coverage`` and ``diff`` carry only their argument
surface and report the milestone that fills them in, so running one early says
what is missing rather than failing in a way that looks like a broken install.
"""

import argparse
import os
import sys


def _not_yet(name, milestone):
    def _run(args):
        print("dvflow-doc %s: not implemented yet (planned for %s)" % (
            name, milestone), file=sys.stderr)
        return 2
    return _run


def _report(markers):
    """Print loader diagnostics to stderr, with their source location.

    stderr, not stdout: `dump` is meant to be piped into a golden file or `jq`,
    and a warning mixed into that stream would corrupt it.
    """
    for m in markers:
        loc = m.location()
        print("%s: %s%s" % (m.severity, m.msg, (" (%s)" % loc) if loc else ""),
              file=sys.stderr)


def _cmd_dump(args):
    """Print the extracted model as JSON.

    This is the same document the Sphinx directives render, which is what makes
    it useful for more than debugging: a disagreement between a rendered page
    and this output is a renderer bug, and there is no third place to look.
    """
    from dv_flow.doc.export.json_ import dumps
    from dv_flow.doc.loader import find_task, load_project
    from dv_flow.doc.package import documented_tasks, extract_package
    from dv_flow.doc.task import extract_task

    result = load_project(args.root)
    _report(result.markers)
    if not result.ok:
        return 1

    base = os.path.abspath(args.root) if args.relative else None

    if args.name:
        task = find_task(result.pkg, args.name)
        if task is None:
            print("no task named '%s' in package '%s'" % (
                args.name, result.pkg.name), file=sys.stderr)
            return 1
        doc = extract_task(task, result.pkg, result.loader)
        print(dumps(doc, base_dir=base))
        return 0

    payload = {
        "package": extract_package(
            result.pkg, internal=args.internal).to_dict(),
        "tasks": [extract_task(t, result.pkg, result.loader).to_dict()
                  for t in documented_tasks(result.pkg, internal=args.internal)],
    }
    print(dumps(payload, base_dir=base))
    return 0


def _getParser():
    parser = argparse.ArgumentParser(
        prog="dvflow-doc",
        description="Extract documentation facts from a DV Flow project.")
    parser.add_argument(
        "--version", action="store_true",
        help="Print the sphinx-dv-flow version and exit")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    dump = subparsers.add_parser(
        "dump", help="Print the extracted model as JSON")
    dump.add_argument(
        "name", nargs="?",
        help="Task to dump. Omit to dump the package and every documented "
             "task in it. Unqualified names are resolved against the package.")
    dump.add_argument(
        "-r", "--root", default=".",
        help="Project root to load (default: the current directory)")
    dump.add_argument(
        "--internal", action="store_true",
        help="Include package-internal tasks (never `local` ones -- a "
             "fragment-scoped task is not addressable by a reader)")
    dump.add_argument(
        "--relative", action="store_true",
        help="Emit source paths relative to the root, so the output does not "
             "depend on where the checkout lives. Used by the golden tests.")
    dump.set_defaults(func=_cmd_dump)

    coverage = subparsers.add_parser(
        "coverage", help="Report tasks and parameters lacking documentation")
    coverage.add_argument(
        "-r", "--root", default=".",
        help="Project root to load (default: the current directory)")
    coverage.set_defaults(func=_not_yet("coverage", "M5"))

    diff = subparsers.add_parser(
        "diff", help="Compare the documented interface of two revisions")
    diff.add_argument("old", help="Baseline model JSON, or a project root")
    diff.add_argument("new", help="Candidate model JSON, or a project root")
    diff.set_defaults(func=_not_yet("diff", "M7"))

    return parser


def main(args=None):
    parser = _getParser()
    ns = parser.parse_args(args)

    if getattr(ns, "version", False):
        from dv_flow.doc import __version__
        print(__version__)
        return 0

    if getattr(ns, "func", None) is None:
        parser.print_help()
        return 1

    return ns.func(ns)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

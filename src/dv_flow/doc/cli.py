"""``dvflow-doc`` -- the extractor, without Sphinx in the way.

The subcommands here exist so the extraction contract can be inspected, diffed
and tested as data. ``dump`` in particular is what golden tests compare against,
which means the JSON it emits is a real interface: if a Sphinx directive shows
a fact, this command can print it.

M0 ships the argument surface and no behavior. Each subcommand reports the
milestone that fills it in, so running one early says what is missing rather
than failing in a way that looks like a broken install.
"""

import argparse
import sys


def _not_yet(name, milestone):
    def _run(args):
        print("dvflow-doc %s: not implemented yet (planned for %s)" % (
            name, milestone), file=sys.stderr)
        return 2
    return _run


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
        "-r", "--root", default=".",
        help="Project root to load (default: the current directory)")
    dump.set_defaults(func=_not_yet("dump", "M1"))

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

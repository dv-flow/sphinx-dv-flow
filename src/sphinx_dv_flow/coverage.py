"""The build-time coverage report (design §10).

A generated doc set hides missing documentation particularly well: every public
task gets a heading and a parameter table whether or not anyone described it,
so the output looks complete at exactly the density where it is emptiest. This
turns that into something visible -- a summary line in the build log and an
artifact next to the built pages.

Three deliberate choices:

*Off by default.* A report nobody asked for that appears in every build is
noise, and noise in a build log is how warnings stop being read.

*Not a warning by default.* An undocumented task is a finding, not a broken
build. Making it a warning would fail every `-W` build over a missing sentence,
and the response to that is to switch the report off -- losing all of it.
`dvflow_coverage_warn` is there for a project that has decided otherwise.

*Reported over what this doc set loaded*, not over the whole flow project. The
question a coverage report answers is "what did I publish undocumented", and a
package the doc set never mentions cannot answer it.
"""

import os

from sphinx.util import logging

logger = logging.getLogger(__name__)

# Written next to the built pages rather than into the doc source: it is a
# product of the build, and a report checked into a source tree goes stale
# silently.
ARTIFACT = "dvflow-coverage.txt"


def _projects(app):
    """The projects this build loaded, or the configured one as a fallback.

    The fallback is what makes the report survive a parallel read: each worker
    has its own cache, so the main process may finish the build having loaded
    nothing itself.
    """
    from . import env as env_module
    from .config import project_root

    cache = env_module._projects.get(str(app.env.srcdir), {})
    if cache:
        return [(root, result) for (root, _config), result in cache.items()]

    root = project_root(app.env)
    from dv_flow.doc.loader import load_project
    return [(root, load_project(root, config=app.config.dvflow_config))]


def report(app, exception):
    """Wired to `build-finished`."""
    if exception is not None or not app.config.dvflow_coverage:
        return

    from dv_flow.doc.coverage import build, format_text

    sections = []
    findings = []
    counted = 0
    documented = 0

    for root, result in sorted(_projects(app)):
        if not result.ok:
            continue
        rep = build(result.pkg, result.loader,
                    internal=app.config.dvflow_internal)
        findings.extend(rep.findings)
        counted += rep.total
        documented += rep.documented
        sections.append("# %s\n%s" % (root, format_text(rep, base_dir=root)))

    if not sections:
        return

    path = os.path.join(app.outdir, ARTIFACT)
    try:
        with open(path, "w") as fp:
            fp.write("\n".join(sections))
    except OSError as e:
        logger.warning("could not write %s: %s", ARTIFACT, e,
                       type='dvflow', subtype='coverage')
        path = None

    percent = 100.0 if not counted else 100.0 * documented / counted
    logger.info("dv-flow documentation coverage: %d/%d (%.0f%%), %d missing%s",
                documented, counted, percent, len(findings),
                (" — see %s" % ARTIFACT) if path else "")

    if app.config.dvflow_coverage_warn:
        for finding in findings:
            logger.warning(
                "undocumented: %s", finding.describe(),
                # Located at the flow file, not at the `.rst` that happened to
                # generate the page: the fix is a `desc:` in the flow file, and
                # that is where the reader has to end up.
                location=finding.location() or None,
                type='dvflow', subtype='coverage')

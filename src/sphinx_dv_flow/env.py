"""Loading a flow project once per build, and turning its markers into warnings.

Loading is not cheap, and a directive-per-load would make a large doc set
unusable, so results are cached for the duration of a build.

**The cache cannot live on the build environment.** Sphinx pickles the
environment at the end of every build, and a loaded package holds pydantic
parameter models that `ParamBuilder` creates at runtime -- classes with no
module-level name to look up, so pickling raises. Storing the result on `env`
therefore does not merely bloat the environment file: it fails the build
outright, after all the pages have rendered, with an error that names a
generated class and gives no hint of where it came from.

So the cache is module-level, keyed by source directory, and cleared when a
builder is initialised. Module-level is also correct for parallel reads: each
worker is a separate process with its own cache, and a loaded package is not
something to share across processes anyway.

The cache is deliberately not persisted across builds. Nothing here can tell
when a flow file changed, and a cache that cannot be invalidated is a bug
waiting for someone to edit a flow file and not see it -- `note_dependency`
handles that case properly instead.
"""

import os

from sphinx.util import logging

logger = logging.getLogger(__name__)

# {srcdir: {(root, config): LoadResult}}
_projects = {}


def purge(app=None, *args):
    """Drop cached projects. Wired to `builder-inited`.

    Matters most in the test suite, where several apps are built in one
    process: without this, a doc root would see whatever the previous test
    loaded from the same source directory.
    """
    _projects.clear()


def load(env, root, config=None, location=None):
    """Load (or fetch from cache) the project at `root`.

    Returns a `LoadResult`, always -- a failed load is reported through the
    result, not by raising. A directive has to warn and carry on: raising would
    turn one bad flow file into a build with no output at all.

    Markers are reported once per (root, config), on first load. Reporting them
    per directive would repeat the same parse error for every task on the page,
    which trains a reader to skip the warnings.
    """
    from dv_flow.doc.loader import load_project

    cache = _projects.setdefault(str(env.srcdir), {})

    key = (os.path.abspath(root), config)
    if key in cache:
        return cache[key]

    result = load_project(root, config=config)
    cache[key] = result

    report_markers(result.markers, location=location)

    return result


def report_markers(markers, location=None):
    """Forward loader diagnostics as Sphinx warnings, with their own location.

    The location is the *flow file*, not the document that referenced it. That
    is the whole point: a broken flow file should send the reader to the line
    that is broken, rather than to the `.rst` that happened to mention the task.
    """
    for marker in markers:
        loc = marker.location() or location
        if marker.is_error:
            logger.warning("%s", marker.msg, location=loc,
                           type='dvflow', subtype='load')
        else:
            logger.info("dv-flow: %s%s", marker.msg,
                        (" (%s)" % loc) if loc else "")


def note_dependencies(env, result):
    """Register every contributing flow file with the build environment.

    Without this, editing a flow file leaves the generated page stale on an
    incremental build and there is nothing to suggest why -- the `.rst` did not
    change, so Sphinx has no reason to think the page did.
    """
    for path in result.flow_files():
        try:
            env.note_dependency(path)
        except Exception:
            # A dependency that cannot be registered costs incrementality for
            # that file. It is not worth failing a build over.
            pass

"""Source links from a documented object to the flow file that declares it.

Every object already renders a ``Defined in flow.yaml:NN`` line. With
``dvflow_viewcode`` enabled -- the default -- that line becomes a link to a
generated, syntax-highlighted listing of the flow file, anchored at the
declaration.

Modeled on ``sphinx.ext.viewcode``, and on ``sphinx_systemverilog.viewcode``
which does the same thing for SystemVerilog sources. Self-contained by design:
no repository URL, branch or commit is configured anywhere, because a flow file
is often not in the documentation's own repository at all -- it may come from an
installed distribution, as ``dv-flow-libproject``'s three packages do -- and a
blob URL guessed for one is wrong for the other. A listing built from the file
the build actually read is correct in both cases.

The reference node is emitted unconditionally by `render.blocks.source`, which
has no access to configuration. Whether it *stays* a link is decided here: with
viewcode off, or on a non-HTML builder, `resolve_links` unwraps it and the
reader is left with the same plain text as before.
"""

from __future__ import annotations

import os
import posixpath
import re

from docutils import nodes
from sphinx.util import logging

logger = logging.getLogger(__name__)

#: Page-name prefix for generated listings.
_PAGE_PREFIX = "_flow_source"


def _norm(file_path):
    return os.path.abspath(file_path)


def display_path(file_path, confdir):
    """How the listing names itself: relative to the doc source when possible.

    A flow project's files are very often all called ``flow.yaml`` -- this
    library's own three packages are -- so a page titled with the basename
    alone would give three different listings the same name. The path relative
    to ``conf.py`` distinguishes them and is the form a reader can act on.
    """
    path = _norm(file_path)
    if confdir:
        try:
            return os.path.relpath(path, confdir)
        except ValueError:
            pass
    return path


def page_name(file_path, confdir=None):
    """Stable, URL-safe page name for a source file.

    Derived from the path relative to ``conf.py`` rather than from the absolute
    path, so the generated URL is the same on a developer's machine and in CI.
    An absolute path would put ``/home/<someone>`` in a published URL and
    change the page name -- and every link to it -- with the checkout location.
    """
    rel = display_path(file_path, confdir)
    # `..` segments become `up`, not dots. Mangling them directly yields a page
    # name starting with `..`, which lands on disk as a DOTFILE -- invisible to
    # `ls`, and dropped by any deploy that excludes `.*`, leaving every source
    # link pointing at a 404 that nothing in the build reported. Flow files
    # sitting outside the documentation directory is the normal case, not an
    # edge one: this library's own are two levels up.
    parts = ['up' if p == os.pardir else p
             for p in rel.split(os.sep) if p and p != os.curdir]
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", "_".join(parts)).strip("_.")
    return posixpath.join(_PAGE_PREFIX, safe or "source")


def _store(env):
    if not hasattr(env, 'dvflow_viewcode'):
        env.dvflow_viewcode = {}
    return env.dvflow_viewcode


def make_source_node(text, file_path, line):
    """The ``Defined in ...`` line, as a reference awaiting resolution.

    Carries the target as node attributes rather than a URI: the page it points
    at does not exist yet during the read phase, and the relative URI depends on
    which document is being written.
    """
    ref = nodes.reference('', '', nodes.emphasis(text=text),
                          refuri='#', internal=True)
    ref['dvflow_viewcode_target'] = _norm(file_path)
    ref['dvflow_viewcode_line'] = line
    return ref


def record(app, doctree):
    """`doctree-read` handler: note which files and lines are linked.

    Recorded during the read phase, on the environment, so that a parallel read
    can merge the contributions (`merge_info`). Collecting at write time
    instead would lose every file whose page was rendered in a worker process.
    """
    if not app.config.dvflow_viewcode:
        return
    store = _store(app.env)
    for ref in doctree.findall(nodes.reference):
        target = ref.get('dvflow_viewcode_target')
        if target:
            store.setdefault(target, set()).add(ref['dvflow_viewcode_line'])


def merge_info(app, env, docnames, other):
    """`env-merge-info` handler. Required for `parallel_read_safe`."""
    merged = getattr(other, 'dvflow_viewcode', None)
    if not merged:
        return
    store = _store(env)
    for path, lines in merged.items():
        store.setdefault(path, set()).update(lines)


def purge(app, env, docname):
    """`env-purge-doc` handler.

    Deliberately a no-op: the store is keyed by source file, not by document,
    and a flow file stays worth listing when one of several documents
    describing it is re-read. The cost of never shrinking is one extra listing
    page for a file nothing references any more.
    """


def resolve_links(app, doctree, fromdocname):
    """`doctree-resolved` handler: point each reference at its listing.

    Resolved this late because the relative URI depends on the document being
    written, and because a reference that cannot be resolved has to degrade to
    the plain text it wraps rather than to a broken link.
    """
    builder = app.builder
    enabled = (app.config.dvflow_viewcode
               and getattr(builder, 'format', None) == 'html')
    for ref in list(doctree.findall(nodes.reference)):
        if not ref.get('dvflow_viewcode_target'):
            continue
        if not enabled:
            ref.replace_self(ref.children)
            continue
        pagename = page_name(ref['dvflow_viewcode_target'], app.confdir)
        try:
            uri = builder.get_relative_uri(fromdocname, pagename)
        except Exception:
            ref.replace_self(ref.children)
            continue
        ref['refuri'] = uri + "#flowline-%d" % ref['dvflow_viewcode_line']


def collect_pages(app):
    """`html-collect-pages` handler: one highlighted listing per flow file."""
    store = getattr(app.env, 'dvflow_viewcode', None)
    if not store or not app.config.dvflow_viewcode:
        return
    highlighter = app.builder.highlighter
    for file_path, lines in store.items():
        try:
            with open(file_path, encoding='utf-8', errors='replace') as fp:
                text = fp.read()
        except OSError as e:
            # Not fatal. The file was readable when the flow project loaded, so
            # this is something about the build machine rather than about the
            # documentation -- and a missing listing costs a link, not a page.
            logger.warning("could not read %s for a source listing: %s",
                           file_path, e, type='dvflow', subtype='viewcode')
            continue
        title = display_path(file_path, app.confdir)
        yield (page_name(file_path, app.confdir),
               {'title': title,
                'body': "<h1>%s</h1>\n%s" % (
                    title, _highlight(highlighter, text, lines))},
               'page.html')


def _highlight(highlighter, text, lines):
    """Highlight the flow file, anchoring the lines that are linked to."""
    try:
        body = highlighter.highlight_block(text, 'yaml', linenos=False)
    except Exception:
        # A flow file that Pygments cannot lex still has to produce a readable
        # listing: the anchors are the point, the colours are not.
        body = highlighter.highlight_block(text, 'text', linenos=False)

    out = []
    for lineno, raw in enumerate(body.splitlines(), start=1):
        anchor = ('<span id="flowline-%d"></span>' % lineno
                  if lineno in lines else '')
        out.append(anchor + raw)
    return "\n".join(out)

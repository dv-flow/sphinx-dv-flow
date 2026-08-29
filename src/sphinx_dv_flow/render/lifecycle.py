"""Lifecycle banners (design §13 P1).

Rendered **before** the description, and as an admonition rather than a
sentence in the prose. Both choices are about the same reader: someone
skimming a page to decide whether to depend on a task. They will not reach a
note at the bottom, and they will skip a sentence that looks like the rest of
the paragraph.
"""

from docutils import nodes

from dv_flow.doc.lifecycle import read


def _task_ref(name):
    """A replacement task, as a cross-reference.

    A pending reference rather than literal text, because "use X instead" is
    only actionable if the reader can get to X. When the replacement lives in
    another package that this doc set does not cover, the reference does not
    resolve and degrades to the name -- which still tells them what to search
    for.
    """
    from sphinx import addnodes

    ref = addnodes.pending_xref(
        '', refdomain='dvf', reftype='task', reftarget=name,
        refexplicit=False, refwarn=False)
    ref += nodes.literal(text=name)
    return ref


def banner(doc):
    """The lifecycle admonition for `doc`, or nothing."""
    lifecycle = read(doc.tags)

    if lifecycle.is_deprecated:
        body = nodes.paragraph()
        body += nodes.strong(text="Deprecated. ")
        if lifecycle.reason:
            body += nodes.Text(lifecycle.reason)
        else:
            body += nodes.Text("This task should no longer be used.")
        if lifecycle.since:
            body += nodes.Text(" (since %s)" % lifecycle.since)
        body += nodes.Text(" ")
        if lifecycle.replacement:
            body += nodes.Text("Use ")
            body += _task_ref(lifecycle.replacement)
            body += nodes.Text(" instead.")
        else:
            # An empty `replacement` is a statement, not an omission: it says
            # there is nothing to move to. Saying so is what stops a reader
            # from assuming the replacement was simply left unnamed and going
            # looking for it.
            body += nodes.Text("There is no replacement.")
        node = nodes.warning()
        node += body
        return [node]

    if lifecycle.is_experimental:
        body = nodes.paragraph()
        body += nodes.strong(text="Experimental. ")
        body += nodes.Text(
            "This task may change or disappear without a deprecation cycle.")
        if lifecycle.reason:
            body += nodes.Text(" %s" % lifecycle.reason)
        node = nodes.note()
        node += body
        return [node]

    # A declared `Stable` gets a badge on the header line but no banner. It is
    # the assumed state, so an admonition saying so would be noise on every
    # page that bothered to declare it -- and would compete with the banners
    # that carry an actual warning.
    return []


def badge_text(doc):
    """The header-line label, or None when nothing was declared.

    Absence is not a claim: an untagged task is assumed stable and gets no
    badge. Giving every untagged task one would make the badge meaningless and
    bury the tasks that actually said something.
    """
    lifecycle = read(doc.tags)
    return lifecycle.status if lifecycle.declared else None

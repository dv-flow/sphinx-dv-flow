"""Parsing a ``doc:`` field as reStructuredText, with source mapping.

A ``doc:`` field is prose the author wrote in a YAML block scalar. It should be
able to contain markup -- a list, a code block, a cross-reference -- because
otherwise the extension's answer to "how do I document this properly" is "don't
use the field designed for it".

Two things this has to get right:

**Dedent.** YAML block scalars arrive with the block's own indentation stripped
by the YAML parser but any *relative* indentation intact, and reStructuredText
treats a uniformly-indented block as a blockquote. Without dedenting, prose that
looked fine in the flow file renders inside a quote box.

**Source mapping.** Errors in that markup have to point at the flow file, not at
the ``.rst`` that invoked the directive. A reader told "line 4" of a document
they did not write cannot act on it.
"""

import textwrap

from docutils.statemachine import StringList


def parse_doc(text, state, source=None, line=0):
    """Parse `text` as rST and return the resulting nodes.

    `source` and `line` locate the text in the *flow file*, so a markup error
    is reported against what the author actually wrote.
    """
    from docutils import nodes

    container = nodes.Element()
    if not text:
        return container.children

    lines = textwrap.dedent(text).splitlines()
    src = source or "<dvflow>"
    content = StringList(lines, source=src,
                         items=[(src, line + i) for i in range(len(lines))])

    state.nested_parse(content, 0, container)
    return container.children


def first_paragraph(text):
    """The lead sentence of a `doc:` field, for use where one line fits.

    Splits on the first blank line rather than the first newline: prose is
    wrapped in a flow file, so taking one physical line would cut a sentence in
    half.
    """
    if not text:
        return ""
    return " ".join(
        line.strip()
        for line in text.strip().split("\n\n")[0].splitlines()).strip()

"""Parsing a ``doc:`` field, with source mapping (design §8).

A ``doc:`` field is prose the author wrote in a YAML block scalar. It should be
able to contain markup -- a list, a code block, a cross-reference -- because
otherwise the extension's answer to "how do I document this properly" is "don't
use the field designed for it".

Three things this has to get right:

**Dedent.** YAML block scalars arrive with the block's own indentation stripped
by the YAML parser but any *relative* indentation intact, and reStructuredText
treats a uniformly-indented block as a blockquote. Without dedenting, prose that
looked fine in the flow file renders inside a quote box.

**Source mapping.** Errors in that markup have to point at the flow file, not at
the ``.rst`` that invoked the directive. A reader told "line 4" of a document
they did not write cannot act on it.

**Format.** ``doc:`` is not read only by Sphinx. The same string reaches
``dfm show``, ``dfm llms``, and any editor showing a hover -- none of which
render reStructuredText. So flow-file prose is very often written in Markdown,
which is what people type when the consumer is a terminal. ``dvflow_doc_format``
picks the interpretation; see :func:`parse_doc`.
"""

import re
import textwrap

from docutils.statemachine import StringList

#: Formats `dvflow_doc_format` accepts.
FORMATS = ('rst', 'markdown', 'plain')

# A fenced code block: ```lang ... ```
_FENCE = re.compile(r'^(\s*)```+([A-Za-z0-9_+-]*)\s*$')


def _format_of(state, override=None):
    if override:
        return override
    try:
        return state.document.settings.env.config.dvflow_doc_format
    except AttributeError:
        return 'rst'


def markdown_to_rst(text):
    """Convert the Markdown that actually appears in flow-file prose.

    Deliberately **not** a Markdown implementation. It handles the two
    constructs that make otherwise-fine prose fail to parse as
    reStructuredText, and leaves everything else alone:

    - a fenced code block (```` ```yaml ```` ... ```` ``` ````) becomes a
      ``.. code-block::``;
    - a single-backtick code span becomes a double-backtick literal.

    Everything else -- ``**bold**``, ``*emphasis*``, bullet lists, paragraphs,
    blockquotes -- already means the same thing in both, which is why a
    conversion this small is worth having at all. Where it is not enough,
    ``myst_parser`` handles the general case (see :func:`parse_doc`) and
    ``plain`` is always safe.

    Anything unhandled degrades to *rendering oddly*, never to a broken build:
    the caller falls back to ``plain`` when the converted text still fails to
    parse.
    """
    out = []
    fence_indent = None
    for raw in text.splitlines():
        match = _FENCE.match(raw)
        if match and fence_indent is None:
            indent, lang = match.group(1), match.group(2)
            fence_indent = indent
            out.append("%s.. code-block:: %s" % (indent, lang or 'text'))
            out.append("")
            continue
        if match and fence_indent is not None:
            fence_indent = None
            out.append("")
            continue
        if fence_indent is not None:
            # Inside a fence: indent into the code-block body, and never touch
            # the contents. Backticks in code are code.
            out.append("   " + raw)
            continue
        out.append(_code_spans(raw))
    return "\n".join(out)


def _code_spans(line):
    """`x` -> ``x``, leaving existing ``x`` and RST roles alone."""
    if '`' not in line:
        return line
    # Protect what is already correct: double-backtick literals and
    # :role:`target` constructs, both of which a naive substitution would break.
    protected = []

    def hide(match):
        protected.append(match.group(0))
        return "\x00%d\x00" % (len(protected) - 1)

    line = re.sub(r'``[^`]*``|:[a-zA-Z:+._-]+:`[^`]*`|`[^`]*`_', hide, line)
    line = re.sub(r'`([^`\n]+)`', r'``\1``', line)
    return re.sub(r'\x00(\d+)\x00', lambda m: protected[int(m.group(1))], line)


def _plain_nodes(text, source=None, line=0):
    """The prose, uninterpreted.

    Paragraphs stay paragraphs and an indented block stays indented, but no
    markup is recognized -- so nothing can fail to parse. This is the fallback
    whenever an interpretation does not work, because losing the formatting of
    a paragraph is a much smaller failure than losing the paragraph.
    """
    from docutils import nodes

    out = []
    for block in re.split(r'\n\s*\n', text.strip()):
        if not block.strip():
            continue
        if block.startswith((' ', '\t')) or block.lstrip().startswith('```'):
            stripped = block.replace('```', '').rstrip()
            out.append(nodes.literal_block(stripped, textwrap.dedent(stripped)))
        else:
            out.append(nodes.paragraph(text=" ".join(
                l.strip() for l in block.splitlines())))
    return out


def _parse_rst(text, state, source=None, line=0):
    from docutils import nodes

    container = nodes.Element()
    lines = text.splitlines()
    src = source or "<dvflow>"
    content = StringList(lines, source=src,
                         items=[(src, line + i) for i in range(len(lines))])
    state.nested_parse(content, 0, container)
    return container.children


def _has_errors(children):
    from docutils import nodes

    return any(isinstance(node, nodes.system_message)
               or list(node.findall(nodes.system_message))
               for node in children
               if isinstance(node, nodes.Element))


def parse_doc(text, state, source=None, line=0, format=None):
    """Parse `text` and return the resulting nodes.

    `source` and `line` locate the text in the *flow file*, so a markup error
    is reported against what the author actually wrote.

    The interpretation follows ``dvflow_doc_format``:

    ``rst``
        reStructuredText. The default, and the right answer for a project whose
        flow files are written alongside a Sphinx doc set.
    ``markdown``
        ``myst_parser`` when it is installed, otherwise the small conversion in
        :func:`markdown_to_rst`.
    ``plain``
        No markup at all. Always safe.

    Whatever the format, a parse that produces errors falls back to ``plain``
    rather than emitting docutils system messages into the page. Ground rule
    §0.4: prose a person wrote is worth showing even when its markup is wrong,
    and the build should say so once rather than fail.
    """
    if not text:
        return []

    text = textwrap.dedent(text)
    fmt = _format_of(state, format)

    if fmt == 'plain':
        return _plain_nodes(text, source, line)

    if fmt == 'markdown':
        parsed = _parse_markdown(text, state, source, line)
        if parsed is not None:
            return parsed

    children = _parse_rst(text, state, source, line)
    if _has_errors(children):
        # The prose does not parse as declared. Show it rather than showing
        # docutils' complaint about it -- the reader wants the sentence, and the
        # author gets the error through the normal warning stream.
        return _plain_nodes(text, source, line)
    return children


def _parse_markdown(text, state, source=None, line=0):
    """Markdown via myst-parser, or None to fall through to the conversion."""
    try:
        from myst_parser.parsers.docutils_ import Parser  # noqa: F401
    except ImportError:
        converted = markdown_to_rst(text)
        children = _parse_rst(converted, state, source, line)
        return _plain_nodes(text, source, line) if _has_errors(children) \
            else children

    from docutils import nodes

    container = nodes.Element()
    try:
        from myst_parser.mocking import MockState  # noqa: F401
        # myst is installed: let Sphinx's own myst machinery parse the block,
        # which handles the general case rather than the two constructs the
        # local conversion knows about.
        from myst_parser.parsers.sphinx_ import MystParser

        parser = MystParser()
        document = state.document.copy()
        parser.parse(text, document)
        container += document.children
        return container.children
    except Exception:
        return None


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

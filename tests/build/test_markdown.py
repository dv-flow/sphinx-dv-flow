"""`doc:` prose written in Markdown, through both implementations.

`dvflow_doc_format = "markdown"` has two: myst-parser when the doc set enables
it, and the small conversion in `render.docfield.markdown_to_rst` otherwise.
Both have to render the same fixture without complaining, because the setting
is a statement about the flow file -- not about what the documentation project
happens to have installed.

The case worth a test of its own is myst INSTALLED BUT NOT ENABLED, which is
ordinary: myst arrives as a dependency of something else, or through this
package's `markdown` extra, in a project whose own `extensions` never mention
it. `MystParser.parse` reads `env.myst_config`, attached by myst_parser's
`setup()`, so in that state it raised into a bare `except` and the text was
handed to the reStructuredText parser instead. A fenced code block is an
indentation error in RST, so well-formed Markdown produced docutils errors
pointing into the flow file.
"""

import os

import pytest


def _read(app, *parts):
    with open(os.path.join(str(app.outdir), *parts), encoding='utf-8') as fp:
        return fp.read()


@pytest.mark.sphinx('html', testroot='markdown')
def test_markdown_renders_without_myst_enabled(app, warning):
    app.build()
    assert warning.getvalue().strip() == ""


@pytest.mark.sphinx('html', testroot='markdown')
def test_the_fenced_block_becomes_a_code_block(app):
    """The construct that told us which parser ran. Under RST it is an error;
    under either Markdown implementation it is a literal block."""
    app.build()
    html = _read(app, 'index.html')
    # `highlight-yaml`, not the literal text: the fence names a language and
    # Pygments splits the body into per-token spans, so the source line does
    # not survive as a contiguous string. The class is the evidence that the
    # fence was understood rather than merely escaped.
    assert 'highlight-yaml' in html
    assert 'use-it' in html


@pytest.mark.sphinx('html', testroot='markdown')
def test_ordinary_markdown_survives(app):
    app.build()
    html = _read(app, 'index.html')
    assert '<strong>default</strong>' in html
    assert '<li>' in html


@pytest.mark.sphinx('html', testroot='markdown-myst')
def test_markdown_renders_with_myst_enabled(app, warning):
    """The documented upgrade path. Skipped rather than failed when myst is
    absent: it is an extra, and a suite that cannot be run without every extra
    installed stops being run."""
    pytest.importorskip("myst_parser")
    app.build()
    assert warning.getvalue().strip() == ""
    html = _read(app, 'index.html')
    assert 'highlight-yaml' in html
    assert '<strong>default</strong>' in html

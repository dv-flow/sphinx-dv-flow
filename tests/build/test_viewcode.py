"""Source links from a documented object to the flow file that declares it.

The point of the feature is that the generated reference can be checked against
the declaration it was generated from, so what these tests pin is the round
trip: a link exists, the page it names was written, and the anchor lands on the
line the text claims.
"""

import os
import re

import pytest


def _read(app, *parts):
    with open(os.path.join(str(app.outdir), *parts), encoding='utf-8') as fp:
        return fp.read()


def _source_links(html):
    """`[(href, text)]` for every rendered `Defined in ...` line."""
    return re.findall(
        r'<p class="dvf-source"><a[^>]*href="([^"]+)"[^>]*>'
        r'<em>([^<]+)</em></a></p>', html)


@pytest.mark.sphinx('html', testroot='viewcode')
def test_a_documented_task_links_to_its_declaration(app):
    app.build()
    links = _source_links(_read(app, 'index.html'))
    assert links, "no source links were rendered"
    for href, text in links:
        assert '_flow_source/' in href
        assert '#flowline-' in href
        assert text.startswith('Defined in ')


@pytest.mark.sphinx('html', testroot='viewcode')
def test_the_listing_page_exists_and_is_not_a_dotfile(app):
    """A page name derived from a path outside the docs tree starts with `..`
    unless something intervenes, and lands on disk as a dotfile -- invisible,
    and dropped by any deploy that excludes `.*`. The link would still be
    emitted, so nothing in the build would report it."""
    app.build()
    listings = os.listdir(os.path.join(str(app.outdir), '_flow_source'))
    assert listings
    assert not [name for name in listings if name.startswith('.')]

    for href, _ in _source_links(_read(app, 'index.html')):
        page = href.split('#')[0].replace('_flow_source/', '')
        assert page in listings, "%s was linked but never written" % page


@pytest.mark.sphinx('html', testroot='viewcode')
def test_the_anchor_lands_on_the_line_the_text_names(app):
    """The claim in the text and the place the link goes have to agree. They
    are computed from the same `srcinfo`, so this is really a check that the
    anchors are injected against the source's own line numbering rather than
    against the highlighter's output."""
    app.build()
    href, text = _source_links(_read(app, 'index.html'))[0]
    page, anchor = href.split('#')
    stated = int(text.rsplit(':', 1)[1])
    assert anchor == 'flowline-%d' % stated

    listing = _read(app, '_flow_source',
                    page.replace('_flow_source/', ''))
    marker = '<span id="flowline-%d"></span>' % stated
    assert marker in listing

    # The anchored line of the listing, stripped of markup, is the source line.
    rendered = listing[listing.index(marker) + len(marker):]
    rendered = re.sub(r'<[^>]+>', '', rendered.splitlines()[0]).strip()

    flow = os.path.join(os.environ['DVFLOW_TEST_ROOT'],
                        'tests', 'data', 'simple', 'flow.yaml')
    with open(flow, encoding='utf-8') as fp:
        actual = fp.read().splitlines()[stated - 1].strip()
    assert actual.startswith(rendered) or rendered.startswith(actual)


# Its own `srcdir`: `sphinx.testing` reuses one output directory per testroot,
# so asserting that `_flow_source/` was never written would otherwise pass or
# fail on whether an enabled build ran first.
@pytest.mark.sphinx('html', testroot='viewcode', srcdir='viewcode-off',
                    confoverrides={'dvflow_viewcode': '0'}, freshenv=True)
def test_disabling_viewcode_leaves_the_text_unlinked(app):
    """Off is not "no source line" -- `dvflow_show_source` already means that.
    Off means the same sentence, without a link, and with no listing pages
    written."""
    app.build()
    html = _read(app, 'index.html')
    assert 'Defined in ' in html
    assert not _source_links(html)
    assert '_flow_source' not in html
    assert not os.path.isdir(os.path.join(str(app.outdir), '_flow_source'))


@pytest.mark.sphinx('text', testroot='viewcode')
def test_a_non_html_builder_degrades_to_plain_text(app):
    """The listing pages are an HTML-builder concept. A text or man build has
    nowhere to point, and a reference left with `refuri="#"` would render as a
    link to the top of the page."""
    app.build()
    text = _read(app, 'index.txt')
    assert 'Defined in ' in text
    assert '_flow_source' not in text

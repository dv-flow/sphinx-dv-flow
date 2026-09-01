"""Flow-file schema cross-links (design §13 P4).

A rendered page says what a task declares; the flow-spec schema says what a
declaration may contain. Those are the two halves of the same question, and
readers fall through the seam between them -- so the structural keys on a page
(`consumes:`, `produces:`, `with:`, `rundir:`) link to their schema entry.

The link is **generated from the key name**. That is the whole design: a field
added to the schema upstream becomes linkable here without anyone touching this
file, and there is no list to fall out of date. What the extension supplies is
the URL template; what the key supplies is the rest.

Off unless `dvflow_schema_url` is set, because there is no correct default --
the spec lives wherever a given project publishes it.
"""

from docutils import nodes


def _url(config, key):
    template = getattr(config, 'dvflow_schema_url', '') or ''
    if not template:
        return None
    if '{key}' not in template:
        # A base URL rather than a template: the key becomes the anchor, which
        # is what `sphinx-jsonschema` produces and what a reader would guess.
        return "%s#%s" % (template.rstrip('#'), key)
    return template.format(key=key)


def config_of(state):
    """The build configuration reachable from a docutils state, or None.

    Read from the state rather than threaded through every renderer: the block
    renderers take an extraction document and nothing else, and giving each of
    them a config parameter to carry one optional link would be a worse trade
    than this lookup.
    """
    try:
        return state.document.settings.env.config
    except AttributeError:
        return None


def label(text, key, state):
    """A field label, linked to its schema entry when one is configured.

    Returns a string when there is no link -- `_field_list` accepts either --
    so the common case adds no nodes and no indirection.
    """
    config = config_of(state) if state is not None else None
    url = _url(config, key) if config is not None else None
    if url is None:
        return text

    ref = nodes.reference('', '', internal=False, refuri=url,
                          reftitle="%s: in the flow-file schema" % key)
    ref += nodes.Text(text)
    return [ref]

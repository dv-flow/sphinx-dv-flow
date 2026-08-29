"""The command-line view of a root task (design §4.1).

Rendered from ``TaskDoc.usage``, which is ``build_usage_info()`` carried
verbatim -- so what a page shows and what ``dfm show task --usage`` prints
cannot disagree.

Options are emitted as a docutils **option list** rather than a table. That is
not cosmetic: Sphinx generates ``-``/``--`` index entries from option list
items, which makes the flags searchable and makes ``:option:`` cross-references
resolve. A table would look similar and do none of that.
"""

from docutils import nodes


def synopsis(doc):
    """The one line a reader copies to run the task."""
    usage = doc.usage or {}
    line = usage.get('usage')
    if not line:
        return []
    block = nodes.literal_block(line, line)
    block['language'] = 'shell'
    return [block]


def _option_string(arg):
    """`-j, --jobs INT` -- the flags, then the value placeholder."""
    parts = []
    if arg.get('short'):
        parts.append(arg['short'])
    if arg.get('name'):
        parts.append(arg['name'])
    text = ", ".join(parts)
    if arg.get('type') and arg['type'] != 'BOOL':
        text += " " + arg['type']
    return text


def _describe(arg, expr_by_param=None):
    """Help text, default, and accepted values for one option.

    `expr_by_param` supplies the source expression a resolved default came
    from. It is looked up from `TaskDoc.params` rather than from `usage`,
    because `build_usage_info` carries only the value -- and showing only `opt`
    hides that it tracks a package variable, while showing only `${{ build }}`
    is useless to a reader (design §4.1). The option *set* still comes from
    `usage` alone; this adds a fact that view does not carry.
    """
    para = nodes.paragraph()

    if arg.get('help'):
        para += nodes.Text(arg['help'])

    default = arg.get('default')
    if default not in (None, ''):
        if para.children:
            para += nodes.Text(" ")
        para += nodes.Text("[default: ")
        para += nodes.literal(text=str(default))
        expr = (expr_by_param or {}).get(arg.get('param'))
        if expr:
            para += nodes.Text(" — from ")
            para += nodes.literal(text=expr)
        para += nodes.Text("]")

    choices = arg.get('choices')
    if choices:
        text = ", ".join(str(c) for c in choices)
        if arg.get('choices_open'):
            # An open set must never be presented as exhaustive: an unlisted
            # value warns rather than fails, and a reader who believes the list
            # is complete has been misled by the rendering.
            text += ", ..."
        if para.children:
            para += nodes.Text(" ")
        para += nodes.emphasis(text="(%s)" % text)

    body = [para]

    documented = [d for d in (arg.get('choices_doc') or []) if d.get('desc')]
    if documented:
        dl = nodes.definition_list()
        for entry in documented:
            item = nodes.definition_list_item()
            term = nodes.term()
            term += nodes.literal(text=str(entry['value']))
            item += term
            definition = nodes.definition()
            definition += nodes.paragraph(text=entry['desc'])
            item += definition
            dl += item
        body.append(dl)

    return body


def _expressions(doc):
    return {p.name: p.default_expr for p in doc.params if p.default_expr}


def option_list(doc):
    """The options a reader can pass on the command line.

    An entry with no `name` is a parameter without a flag -- which includes
    `cli: {hidden: true}`, because `build_usage_info` reports a hidden option
    as having no first-class flag. Those are covered by `define_only_params`
    below, so a hidden option's *parameter* is still documented as reachable
    even though its flag is not advertised.
    """
    usage = doc.usage or {}
    args = [a for a in usage.get('args', []) if a.get('name')]
    if not args:
        return []

    expr_by_param = _expressions(doc)
    olist = nodes.option_list()
    for arg in args:
        item = nodes.option_list_item()
        group = nodes.option_group()
        option = nodes.option()
        option += nodes.option_string(text=_option_string(arg))
        group += option
        item += group
        description = nodes.description()
        description += _describe(arg, expr_by_param)
        item += description
        olist += item

    return [olist]


def define_only_params(doc):
    """Parameters with no flag, each labelled with its `-D` form.

    The point of this block is that *every* parameter is reachable, not only
    the ones that were given flags. Omitting it would leave a reader believing
    a parameter without a flag cannot be set at all.
    """
    usage = doc.usage or {}
    args = [a for a in usage.get('args', []) if not a.get('name')]
    if not args:
        return []

    expr_by_param = _expressions(doc)
    dl = nodes.definition_list()
    for arg in args:
        item = nodes.definition_list_item()
        term = nodes.term()
        term += nodes.literal(text=arg['define'])
        item += term
        definition = nodes.definition()
        definition += _describe(arg, expr_by_param)
        item += definition
        dl += item

    return [dl]

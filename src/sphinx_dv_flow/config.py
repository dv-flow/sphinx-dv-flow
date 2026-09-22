"""``dvflow_*`` settings, and what they mean.

Every setting here has a default that does something sensible, because the
common case -- one flow project, documented from the Sphinx tree that sits
beside it -- should need no configuration at all.
"""

import os


def setup_config(app):
    """Register the settings. Rebuild triggers are chosen per setting.

    The rebuild argument matters more than it looks: ``'env'`` means changing
    the setting invalidates the parsed environment, which is what a setting
    that changes *what gets extracted* has to do. Getting it wrong leaves a
    stale page that only a `-E` build fixes, and nothing suggests why.
    """
    app.add_config_value('dvflow_root', None, 'env')
    app.add_config_value('dvflow_config', None, 'env')
    app.add_config_value('dvflow_internal', False, 'env')
    app.add_config_value('dvflow_show_source', True, 'env')
    # Turn that `Defined in flow.yaml:NN` line into a link to a generated
    # listing of the file. On by default for the same reason `viewcode` is in
    # most doc sets: the generated reference states a fact about a declaration,
    # and the declaration is the one thing a reader may want to check it
    # against. Self-contained -- see `viewcode.py` for why there is no
    # repository-URL setting to go with it.
    app.add_config_value('dvflow_viewcode', True, 'env')
    # How `doc:` prose is interpreted (design §8). `doc:` is not read only by
    # Sphinx -- the same string reaches `dfm show`, `dfm llms` and editor
    # hovers, none of which render reStructuredText -- so flow-file prose is
    # very often Markdown. 'rst' is the default because it is what a project
    # documenting itself with Sphinx will write; 'markdown' and 'plain' are
    # there because that is not every project.
    app.add_config_value('dvflow_doc_format', 'rst', 'env')
    app.add_config_value('dvflow_diagram_depth', 1, 'env')
    app.add_config_value('dvflow_diagram_max_nodes', 40, 'env')
    app.add_config_value('dvflow_diagram_dataflow', True, 'env')
    app.add_config_value('dvflow_diagram_backend', 'mermaid', 'env')
    app.add_config_value('dvflow_elaborate', False, 'env')
    # Where adjacent example files live, relative to the doc source directory.
    # `docs/examples/<task>.rst` is design §9's convention, and it works with no
    # upstream change -- which is why it is on by default rather than opt-in.
    app.add_config_value('dvflow_examples_dir', 'examples', 'env')
    # A synthesized snippet where nothing was authored. On by default: it is
    # cheap, it is labelled, and it beats an empty section for a task nobody
    # has written prose for.
    app.add_config_value('dvflow_examples_generate', True, 'env')
    # Load every flow-fragment example during the build. On by default because
    # an example that no longer parses is worse than no example -- it is
    # indistinguishable from one that works until someone types it.
    app.add_config_value('dvflow_examples_validate', True, 'env')
    # Draw the flow an example declares. Off by default: it is the one part of
    # example handling that costs a second load per example, and a doc set with
    # many full-flow examples should opt into paying for it.
    app.add_config_value('dvflow_examples_diagrams', False, 'env')
    # Packages documented by another project (design §12.3). Names, not URLs:
    # the URL half is `intersphinx_mapping`, which already exists and already
    # knows how to fetch an inventory. What Sphinx cannot know is *which flow
    # packages* are somebody else's to document, and that is the whole of what
    # this setting says.
    app.add_config_value('dvflow_intersphinx_packages', [], 'env')
    # Where the flow-file schema reference is published (design §13 P4). Either
    # a template containing `{key}` or a base URL, in which case the key becomes
    # the anchor. Empty by default: there is no correct default, because the
    # spec lives wherever a given project publishes it.
    app.add_config_value('dvflow_schema_url', '', 'env')
    # Coverage does not change what is extracted -- it reports on it -- so it
    # rebuilds nothing. `''` is off; a truthy value writes the report at the end
    # of the build.
    app.add_config_value('dvflow_coverage', False, '')
    # Whether an undocumented public object is a warning. Off by default and
    # deliberately: coverage is a finding, and turning every finding into a
    # warning would make `-W` fail a build over a missing sentence -- which is
    # how a project turns the report off and stops seeing any of it.
    app.add_config_value('dvflow_coverage_warn', False, '')


def exclude_examples(app, config):
    """Keep the examples directory out of the document set.

    An adjacent example file lives inside the Sphinx source tree, so Sphinx
    reads it as a document of its own: it gets built as a standalone page and
    warns that it is in no toctree -- which fails a `-W` build for doing
    exactly what §9 says to do. The same fragment is then in the output twice,
    once included and once orphaned.

    Excluded here rather than left to every `conf.py` because the extension is
    what decided the directory is special. Wired to `config-inited`, which runs
    before Sphinx enumerates source files.
    """
    directory = config.dvflow_examples_dir
    if not directory:
        return
    pattern = os.path.join(directory, "**")
    if pattern not in config.exclude_patterns:
        config.exclude_patterns = list(config.exclude_patterns) + [pattern]


def documented_elsewhere(config, name) -> bool:
    """Whether `name` belongs to a package another project documents.

    Matched on the package prefix: `std` covers `std.Message` and
    `std.FileSet`, which is how a reader thinks about it and how the import that
    brought it in was written.
    """
    for package in (config.dvflow_intersphinx_packages or []):
        if name == package or name.startswith(package + '.'):
            return True
    return False


def project_root(env, explicit=None):
    """The flow project to load, as an absolute path.

    Resolution order, and why:

    1. an explicit ``:root:`` on the directive -- a doc set may document more
       than one project, and the per-directive option is the only way to say so;
    2. ``dvflow_root`` in ``conf.py``;
    3. the documentation source directory, so a project whose ``docs/`` sits
       next to its ``flow.yaml`` needs no configuration. `loadProjPkgDef`
       searches upward, so this finds the project from anywhere inside it.

    Relative paths are resolved against the documentation source directory, not
    the current working directory: a docs build should not depend on where it
    was invoked from.
    """
    if explicit:
        base = explicit
    elif env.config.dvflow_root:
        base = env.config.dvflow_root
    else:
        return os.path.abspath(env.srcdir)

    if os.path.isabs(base):
        return base
    return os.path.abspath(os.path.join(str(env.srcdir), base))

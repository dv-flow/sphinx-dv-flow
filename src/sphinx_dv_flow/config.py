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

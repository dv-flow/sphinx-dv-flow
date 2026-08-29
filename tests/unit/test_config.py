"""Resolving which flow project a directive documents.

Path resolution is the kind of thing that works on the author's machine and
breaks in CI, so the rules are pinned rather than left to be discovered.
"""

import os

import pytest

from sphinx_dv_flow.config import project_root


class FakeConfig:
    def __init__(self, root=None, config=None):
        self.dvflow_root = root
        self.dvflow_config = config
        self.dvflow_internal = False
        self.dvflow_show_source = True


class FakeEnv:
    def __init__(self, srcdir, root=None):
        self.srcdir = srcdir
        self.config = FakeConfig(root)


def test_explicit_option_wins(tmp_path):
    """A doc set may document more than one project, and the per-directive
    option is the only way to say so."""
    env = FakeEnv(str(tmp_path), root="/from/conf")
    assert project_root(env, "/from/directive") == "/from/directive"


def test_conf_setting_is_used_when_there_is_no_option(tmp_path):
    env = FakeEnv(str(tmp_path), root="/from/conf")
    assert project_root(env) == "/from/conf"


def test_the_source_directory_is_the_default(tmp_path):
    """A project whose `docs/` sits inside it needs no configuration.

    `loadProjPkgDef` searches upward for the flow file, so pointing at the docs
    directory finds the project from anywhere inside it.
    """
    env = FakeEnv(str(tmp_path))
    assert project_root(env) == os.path.abspath(str(tmp_path))


def test_a_relative_path_resolves_against_the_source_dir(tmp_path):
    """Not against the current working directory: a docs build must not depend
    on where it was invoked from."""
    env = FakeEnv(str(tmp_path), root="../project")
    expected = os.path.abspath(os.path.join(str(tmp_path), "../project"))
    assert project_root(env) == expected


def test_a_relative_directive_option_also_resolves(tmp_path):
    env = FakeEnv(str(tmp_path))
    expected = os.path.abspath(os.path.join(str(tmp_path), "sub/proj"))
    assert project_root(env, "sub/proj") == expected

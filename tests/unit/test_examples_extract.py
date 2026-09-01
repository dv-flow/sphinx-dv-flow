"""Example sources and validation (design §9), without Sphinx.

Precedence is the substance here: which source wins, and what a reader is
allowed to assume about each.
"""

import os

import pytest

from dv_flow.doc.examples import (adjacent_path, collect, generate,
                                  is_flow_fragment, validate)
from dv_flow.doc.loader import load_project
from dv_flow.doc.task import extract_task


@pytest.fixture(scope="module")
def loaded():
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "examples")
    result = load_project(root)
    assert result.ok
    return result


def _doc(loaded, name):
    return extract_task(loaded.pkg.task_m[name], loaded.pkg, loaded.loader)


def test_authored_examples_win_over_generated(loaded):
    """The generated snippet exists to fill an empty section. Producing one
    beside a real example would be noise."""
    out = collect(_doc(loaded, 'examples.Compile'))
    assert [e.origin for e in out] == ['flow', 'flow']


def test_generated_when_nothing_is_authored(loaded):
    out = collect(_doc(loaded, 'examples.Bare'))
    assert [e.origin for e in out] == ['generated']


def test_generated_can_be_declined(loaded):
    assert collect(_doc(loaded, 'examples.Bare'), generate_missing=False) == []


def test_adjacent_file_is_added_not_substituted(loaded, tmp_path):
    """Both are deliberate acts by a person. Suppressing a hand-written page
    because someone added an `examples:` entry would delete content silently."""
    (tmp_path / "examples.Compile.rst").write_text("Hand written.\n")
    out = collect(_doc(loaded, 'examples.Compile'),
                  examples_dir=str(tmp_path))
    assert [e.origin for e in out] == ['flow', 'flow', 'file']


def test_adjacent_file_suppresses_the_generated_one(loaded, tmp_path):
    (tmp_path / "examples.Bare.rst").write_text("Hand written.\n")
    out = collect(_doc(loaded, 'examples.Bare'), examples_dir=str(tmp_path))
    assert [e.origin for e in out] == ['file']


def test_adjacent_path_accepts_the_leaf(tmp_path):
    """`library.Compile.rst` is a tedious filename for a doc set covering one
    package."""
    (tmp_path / "Compile.rst").write_text("x\n")
    assert adjacent_path(str(tmp_path), "library.Compile")


def test_qualified_name_wins_over_the_leaf(tmp_path):
    """Two packages documented in one doc set must not collide."""
    (tmp_path / "Compile.rst").write_text("leaf\n")
    (tmp_path / "library.Compile.rst").write_text("qualified\n")
    assert adjacent_path(str(tmp_path), "library.Compile").endswith(
        "library.Compile.rst")


def test_generated_snippet_is_marked(loaded):
    out = generate(_doc(loaded, 'examples.Bare'))
    assert out.origin == 'generated'
    assert 'Synthesized' in out.caption


def test_generated_snippet_for_a_runnable_task_is_a_command(loaded):
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "simple")
    result = load_project(root)
    doc = extract_task(result.pkg.task_m['simple.run'], result.pkg,
                       result.loader)
    doc.examples = []
    out = generate(doc)
    assert out.lang == 'shell'
    assert out.code == 'dfm run simple.run'


def test_only_flow_fragments_are_recognized():
    assert is_flow_fragment("package:\n  name: x\n")
    assert is_flow_fragment("fragment:\n  tasks: []\n")
    # An excerpt cannot be validated: there is no honest way to guess the file
    # around it, and wrapping it in a synthesized package would validate
    # something the author never wrote.
    assert not is_flow_fragment("tasks:\n- name: x\n")
    assert not is_flow_fragment("dfm run x")


def test_a_command_line_is_never_marked_valid(loaded):
    """"Not checked" and "checked and fine" are different claims."""
    out = collect(_doc(loaded, 'examples.Compile'), validate_flow=True)
    assert out[0].valid is None


def test_a_working_fragment_validates(loaded):
    out = collect(_doc(loaded, 'examples.Compile'), validate_flow=True)
    assert out[1].valid is True


def test_a_broken_fragment_is_caught(loaded):
    out = collect(_doc(loaded, 'examples.Broken'), validate_flow=True)
    assert out[0].valid is False
    assert 'NoSuchTask' in out[0].error


def test_validation_carries_the_declaring_location(loaded):
    """A validation failure has to send the reader to the flow file that
    contains the broken snippet."""
    out = collect(_doc(loaded, 'examples.Broken'), validate_flow=True)
    assert out[0].srcinfo is not None
    assert out[0].srcinfo.file.endswith('flow.yaml')

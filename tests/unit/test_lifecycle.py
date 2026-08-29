"""Reading lifecycle tags (design §13 P1).

A lifecycle tag is a claim about interface churn, not runtime behavior. The
tests below are mostly about two distinctions that are easy to collapse and
expensive to get wrong: absence versus a declared "stable", and an empty
replacement versus a missing one.
"""

import os

import pytest

from dv_flow.doc.lifecycle import (Lifecycle, badge, filter_listing, read)
from dv_flow.doc.loader import load_project
from dv_flow.doc.model import TagDoc
from dv_flow.doc.task import extract_task


@pytest.fixture(scope="module")
def docs(request):
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "lifecycle")
    result = load_project(root)
    assert result.ok
    return {name.split('.')[-1]:
            extract_task(task, result.pkg, result.loader)
            for name, task in result.pkg.task_m.items()}


# ---------------------------------------------------------------- statuses

def test_stable(docs):
    lifecycle = read(docs['Current'].tags)
    assert lifecycle.status == 'stable'
    assert lifecycle.since == '1.0'
    assert lifecycle.declared is True


def test_experimental(docs):
    lifecycle = read(docs['Preview'].tags)
    assert lifecycle.is_experimental
    assert lifecycle.reason == 'parameter names are likely to change'


def test_deprecated(docs):
    lifecycle = read(docs['Retired'].tags)
    assert lifecycle.is_deprecated
    assert lifecycle.replacement == 'lifecycle.Current'
    assert lifecycle.since == '1.4'


# ------------------------------------------------- absence is not a claim

def test_an_untagged_task_is_stable_but_undeclared(docs):
    """The assumed state. `declared` is what separates it from a task that
    actually said so -- and it is what stops every untagged task acquiring a
    badge, which would make the badge meaningless."""
    lifecycle = read(docs['Plain'].tags)
    assert lifecycle.status == 'stable'
    assert lifecycle.declared is False


def test_an_untagged_task_gets_no_badge(docs):
    assert badge(read(docs['Plain'].tags)) is None


def test_a_declared_stable_gets_a_badge(docs):
    assert badge(read(docs['Current'].tags)) == 'stable'


# -------------------------------------- an empty replacement is meaningful

def test_a_deprecation_with_no_replacement(docs):
    """"There is nothing to move to" is a statement, not an omission.

    It leads a reader to a different decision than "use X instead", so the
    model has to keep them apart rather than treating both as "no link".
    """
    lifecycle = read(docs['Abandoned'].tags)
    assert lifecycle.is_deprecated
    assert lifecycle.replacement == ''
    assert lifecycle.reason == 'the underlying tool is gone'


def test_a_replacement_outside_the_package_is_still_named(docs):
    """It will not resolve to a link here, and it must not be dropped for it --
    the name is still what the reader needs to go looking for."""
    lifecycle = read(docs['Elsewhere'].tags)
    assert lifecycle.replacement == 'other.Thing'


# ------------------------------------------------------------- precedence

def test_the_most_cautionary_tag_wins():
    """A task tagged both Stable and Deprecated is contradictory, and reporting
    the reassuring half of a contradiction is the wrong way to resolve it."""
    tags = [TagDoc(name='std.Stable', params={'since': '1.0'}),
            TagDoc(name='std.Deprecated', params={'reason': 'gone'})]
    assert read(tags).is_deprecated


def test_deprecated_beats_experimental():
    tags = [TagDoc(name='std.Experimental'), TagDoc(name='std.Deprecated')]
    assert read(tags).is_deprecated


def test_experimental_beats_stable():
    tags = [TagDoc(name='std.Stable'), TagDoc(name='std.Experimental')]
    assert read(tags).is_experimental


# ---------------------------------------------------------- tag recognition

def test_a_project_defined_tag_is_recognised_by_leaf():
    """A project may define its own lifecycle tags deriving from std's, and a
    reader does not care which package a `Deprecated` came from."""
    tags = [TagDoc(name='proj.Deprecated', params={'reason': 'x'})]
    assert read(tags).is_deprecated


def test_an_unrelated_tag_is_ignored():
    tags = [TagDoc(name='std.Test', params={})]
    lifecycle = read(tags)
    assert lifecycle.declared is False


def test_no_tags_at_all():
    assert read([]) == Lifecycle()
    assert read(None) == Lifecycle()


# -------------------------------------------------------------- listings

def test_deprecated_entries_are_dropped_from_a_listing(docs):
    """A listing is a menu -- it answers "what can I use here", and a task
    nobody should use any more is a wrong answer to that question."""
    kept = {d.name for d in filter_listing(docs.values())}
    assert 'lifecycle.Retired' not in kept
    assert 'lifecycle.Abandoned' not in kept
    assert 'lifecycle.Current' in kept
    assert 'lifecycle.Preview' in kept


def test_experimental_entries_are_kept(docs):
    """Experimental says "this may change", not "do not use". Hiding it would
    defeat the point of shipping something before its interface settles."""
    kept = {d.name for d in filter_listing(docs.values())}
    assert 'lifecycle.Preview' in kept


def test_deprecated_entries_can_be_asked_for(docs):
    kept = {d.name for d in filter_listing(docs.values(),
                                           include_deprecated=True)}
    assert 'lifecycle.Retired' in kept

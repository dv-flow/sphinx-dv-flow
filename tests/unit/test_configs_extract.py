"""Extraction of configurations and filters (design §4.7).

Sphinx-free, like everything under `dv_flow.doc`. What these pin is mostly
what extraction refuses to claim: a config's parameters (which do not work
upstream), a local filter (which a reader cannot name), and a fragment's
contents (which are not in the package until the config is selected).
"""

import os

import pytest

from dv_flow.doc.config import (documented_configs, extract_config,
                                find_config, iter_configs)
from dv_flow.doc.filter import (ACTIVE, documented_filters, extract_filter,
                                find_filter, is_local, iter_filters, signature)
from dv_flow.doc.loader import load_project
from dv_flow.doc.package import extract_package


@pytest.fixture(scope="module")
def pkg(request):
    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "configs")
    result = load_project(root)
    assert result.ok, [m.msg for m in result.markers]
    return result.pkg


def test_configs_are_read_from_the_unified_list(pkg):
    """`all_configs`, not `pkg_def.configs`: a package may organize its
    configurations into fragments, and `-c` does not care which file."""
    assert [c.name for c in iter_configs(pkg)] == ['debug', 'fast', 'ci']


def test_config_records_what_it_changes(pkg):
    doc = extract_config(find_config(pkg, 'debug'), pkg)
    assert doc.tasks == ['configs.Build']
    assert doc.types == []
    assert doc.package == 'configs'


def test_config_base_is_carried(pkg):
    assert extract_config(find_config(pkg, 'fast'), pkg).uses == 'debug'


def test_config_fragment_is_named_not_expanded(pkg):
    doc = extract_config(find_config(pkg, 'ci'), pkg)
    assert doc.fragments == ['ci.yaml']


def test_targets_are_qualified(pkg):
    """Leaf matching resolves a name only when it is unique across the whole
    doc set, so an unqualified `Build` silently stops linking as soon as a
    second package has one."""
    doc = extract_config(find_config(pkg, 'ci'), pkg)
    assert doc.types == ['configs.ObjFile']


def test_config_has_no_params_field():
    """PLAN.md U15: neither spelling of a config `with:` does anything
    upstream, so there is nothing honest to put in such a field."""
    from dv_flow.doc.model import ConfigDoc
    import dataclasses as dc
    assert 'params' not in {f.name for f in dc.fields(ConfigDoc)}


def test_config_source_location(pkg):
    """U16 put `srcinfo` on a config. Without it the only location available
    is the whole file."""
    doc = extract_config(find_config(pkg, 'debug'), pkg)
    assert doc.srcinfo is not None
    assert doc.srcinfo.file.endswith('flow.yaml')
    assert doc.srcinfo.line > 0


def test_configs_have_no_visibility(pkg):
    """Anyone who can run the flow can select any configuration. Hiding one
    would make it undiscoverable, not unreachable."""
    assert len(documented_configs(pkg)) == len(iter_configs(pkg))


def test_filters_come_from_package_and_fragments(pkg):
    names = [f.name for f in iter_filters(pkg)]
    assert 'by_arch' in names          # package file
    assert 'basenames_of' in names     # fragment
    assert 'internal_helper' in names  # present, but not documented


def test_local_filter_is_never_documented(pkg):
    assert is_local(find_filter(pkg, 'internal_helper'))
    assert 'internal_helper' not in {
        f.name for f in documented_filters(pkg, internal=True)}


def test_unscoped_filter_is_package_internal(pkg):
    """Same audience model as tasks, read off the same words."""
    assert 'paths_of' not in {f.name for f in documented_filters(pkg)}
    assert 'paths_of' in {f.name for f in documented_filters(pkg, internal=True)}


def test_signature_is_the_call(pkg):
    fd = find_filter(pkg, 'by_arch')
    assert signature(fd) == "${{ inputs | by_arch(arch) }}"


def test_signature_without_arguments(pkg):
    assert signature(find_filter(pkg, 'basenames_of')) == \
        "${{ inputs | basenames_of }}"


def test_arguments_bind_positionally(pkg):
    """Declaration order is part of a filter's interface, not a presentation
    choice, so it is never sorted."""
    doc = extract_filter(find_filter(pkg, 'by_arch'), pkg)
    assert [p.name for p in doc.params] == ['arch']
    assert doc.params[0].define == '$arg0'


def test_filter_body_is_carried(pkg):
    doc = extract_filter(find_filter(pkg, 'by_arch'), pkg)
    assert doc.impl == 'expr'
    assert '$arg0' in doc.body


def test_filters_are_not_active_yet():
    """PLAN.md U14, recorded in one place so renderers do not each decide."""
    assert ACTIVE is False


def test_package_document_lists_both(pkg):
    doc = extract_package(pkg)
    assert doc.configs == ['debug', 'fast', 'ci']
    assert doc.filters == ['by_arch', 'basenames_of']

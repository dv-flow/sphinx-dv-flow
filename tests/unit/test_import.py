"""Both packages import, and the pieces a user names in config actually exist."""

import subprocess
import sys


def test_dv_flow_doc_imports():
    import dv_flow.doc
    assert dv_flow.doc.__version__


def test_sphinx_dv_flow_imports():
    import sphinx_dv_flow
    assert callable(sphinx_dv_flow.setup)


def test_namespace_is_shared_with_dv_flow_mgr():
    """`dv_flow` is an implicit namespace package spanning two distributions.

    An `__init__.py` in either `src/dv_flow/` would shadow the other package,
    and the failure mode is a confusing ImportError at a distance. Importing
    both siblings is the cheapest way to notice.
    """
    import dv_flow.doc
    import dv_flow.mgr
    assert dv_flow.doc.__name__ == "dv_flow.doc"
    assert dv_flow.mgr.__name__ == "dv_flow.mgr"


class RecordingApp:
    """Just enough Sphinx app to see what `setup()` registers.

    A stand-in rather than a real app because the question here is "does the
    entry point wire up what it claims to", which is about the registration
    calls. Whether the registered pieces then *work* is what `tests/build/`
    answers, against a real build.
    """

    def __init__(self):
        self.config_values = []
        self.domains = []
        self.directives = []
        self.indices = []
        self.events = []

    def add_config_value(self, name, default, rebuild, **kw):
        self.config_values.append((name, default, rebuild))

    def add_domain(self, domain):
        self.domains.append(domain)

    def add_directive_to_domain(self, domain, name, cls, **kw):
        self.directives.append((domain, name))

    def add_index_to_domain(self, domain, index, **kw):
        self.indices.append((domain, index.name))

    def connect(self, event, handler, **kw):
        self.events.append(event)


def test_setup_reports_a_version():
    import sphinx_dv_flow
    meta = sphinx_dv_flow.setup(RecordingApp())
    assert meta["version"] == sphinx_dv_flow.__version__


def test_setup_registers_the_domain_and_directives():
    import sphinx_dv_flow
    app = RecordingApp()
    sphinx_dv_flow.setup(app)

    assert [d.name for d in app.domains] == ["dvf"]
    assert set(app.directives) == {
        ("dvf", "autotask"), ("dvf", "autotype"), ("dvf", "autopackage"),
        ("dvf", "flowdiagram"), ("dvf", "inheritance"), ("dvf", "dataflow"),
        ("dvf", "packagediagram"), ("dvf", "elaborated"),
        ("dvf", "autoconfig"), ("dvf", "autofilter")}


def test_setup_registers_the_config_values():
    import sphinx_dv_flow
    app = RecordingApp()
    sphinx_dv_flow.setup(app)

    names = {name for name, _, _ in app.config_values}
    assert names == {"dvflow_root", "dvflow_config", "dvflow_internal",
                     "dvflow_show_source", "dvflow_diagram_depth",
                     "dvflow_diagram_max_nodes", "dvflow_diagram_dataflow",
                     "dvflow_diagram_backend", "dvflow_elaborate",
                     "dvflow_coverage", "dvflow_coverage_warn",
                     "dvflow_examples_dir", "dvflow_examples_generate",
                     "dvflow_examples_validate", "dvflow_examples_diagrams",
                     "dvflow_intersphinx_packages", "dvflow_schema_url"}

    # Every setting that changes WHAT gets extracted must invalidate the
    # environment. A setting that rebuilds on 'html' instead would leave a
    # stale page that only `-E` fixes, with nothing to suggest why.
    extraction = {name: rebuild for name, _, rebuild in app.config_values
                  if not name.startswith('dvflow_coverage')}
    assert set(extraction.values()) == {"env"}

    # The coverage settings are the exception, and deliberately: they report on
    # what was extracted rather than changing it, so re-reading every document
    # because someone asked for a report would be a rebuild for nothing.
    assert {rebuild for name, _, rebuild in app.config_values
            if name.startswith('dvflow_coverage')} == {""}


def test_setup_registers_the_indices():
    """An alphabetical name list is the index a tool produces when nobody
    asked what a reader is looking for. These answer the reverse questions --
    what produces this type, what consumes it, what is deprecated -- which is
    what a flow library makes hard to find out."""
    import sphinx_dv_flow
    app = RecordingApp()
    sphinx_dv_flow.setup(app)

    assert {name for _, name in app.indices} == {
        "tasks", "types", "produced", "consumed", "tags"}


def test_setup_clears_the_project_cache_on_build():
    """The cache is per-build and lives outside the environment (see env.py).

    Without the hook, a second build in the same process reuses whatever the
    first one loaded.
    """
    import sphinx_dv_flow
    app = RecordingApp()
    sphinx_dv_flow.setup(app)
    assert "builder-inited" in app.events


def test_console_script_entry_point_is_callable():
    """`dvflow-doc` names a real function, whether or not it does much yet."""
    from dv_flow.doc.cli import main
    assert callable(main)


def test_cli_with_no_command_prints_help():
    from dv_flow.doc.cli import main
    assert main([]) == 1


def test_cli_version():
    proc = subprocess.run(
        [sys.executable, "-m", "dv_flow.doc.cli", "--version"],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip()

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


def test_setup_reports_a_version():
    import sphinx_dv_flow
    meta = sphinx_dv_flow.setup(app=None)
    assert meta["version"] == sphinx_dv_flow.__version__


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

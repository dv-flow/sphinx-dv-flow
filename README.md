# sphinx-dv-flow

Sphinx support for documenting [DV Flow](https://github.com/dv-flow/dv-flow-mgr)
workflows.

A flow file already states what a task takes, what it produces, and how it is
reached. `sphinx-dv-flow` reads those statements and renders them, so the
documentation says what the flow actually does rather than what it did when
someone last updated a table by hand.

```shell
pip install sphinx-dv-flow
```

```python
# conf.py
extensions = ["sphinx_dv_flow"]
```

```rst
.. dvf:autopackage:: mypkg
   :types:
```

That documents every task the package publishes — parameters with their types
and defaults, what each task consumes and produces, where it sits in the `uses:`
chain, and a diagram of the flow — from the flow file, with no per-task
boilerplate. Individual objects have their own directives (`dvf:autotask`,
`dvf:autotype`, `dvf:autoconfig`, `dvf:autofilter`) and roles (`` :dvf:task:`…` ``)
for cross-referencing, including across projects via `intersphinx`.

## Two packages, one distribution

The split is the one structurally expensive decision in the project, and it is
enforced by a test rather than by intent:

- **`dv_flow.doc`** loads a project and extracts documentation facts as plain
  data. It does not import Sphinx, and an out-of-process test checks that after
  importing it `sphinx` is absent from `sys.modules`. This keeps the extracted
  model testable as data, and reusable by tools — `dfm` among them — that have
  no business depending on a documentation generator.
- **`sphinx_dv_flow`** is the Sphinx extension: directives, roles, indices and
  diagrams. Rendering only.

The dependency runs one way, never the reverse.

## Ground rules

These shaped most of the design decisions and are worth stating up front:

- **Declared over discovered.** Where the flow file says something, that is the
  answer. Inference is labelled as inference.
- **A resolution failure never fails a docs build.** A missing package is a
  warning against the object that referenced it. Only a malformed flow file is
  fatal, and then with a location.
- **Every diagram has a textual twin,** so `text`, `man` and a screen reader
  carry the same facts as the picture.
- **Visibility is the audience model.** `export` and `root` tasks are documented;
  unscoped ones only under `:internal:`; `local` never, because a reader cannot
  address one whatever the documentation says.

## Status

Early. The extraction and rendering layers, the `dvf` domain, diagrams,
examples, coverage reporting and cross-project references are in place, and
`dv-flow-mgr` generates its own standard-library reference with this extension.
The directive and configuration surface is not frozen — hence `0.0.x`.

## Documentation

Built from `docs/`, and by design also the acceptance test for the directives
the extension ships: the build runs under `-W` in CI, so a warning there is a
failure.

## License

Apache-2.0

"""The elaborated instance view (design §6.1) -- opt-in, and labelled.

This is the graph the engine will actually build: matrix cells expanded,
`iff:` resolved, one node per instance. It is produced by
`TaskGraphDotWriter`, which is what `dfm graph` uses -- reused rather than
reimplemented, for the same reason `build_usage_info` is: two renderers of "what
does this graph look like" would eventually disagree, and the documentation is
the half nobody checks against the tool.

The U3 upstream hook (`node_url`) is what makes its nodes clickable.

**Two things this view is not.** It is not the default, and it is not
reproducible. An elaborated graph is one machine's expansion of one
configuration -- a different `-D`, a different environment, a different day and
it is a different picture. So every model this module produces carries
`elaborated=True` and the parameters it was built under, and the renderer says
so on the page. Nobody should mistake one expansion for the definition.
"""

import dataclasses as dc
import os
from typing import Any, Dict, Optional


@dc.dataclass
class Elaborated:
    """Dot source for the instance graph, plus what it was built under."""
    task: str = ""
    dot: str = ""
    # The parameter values in force. Rendered with the diagram, because a graph
    # without them is an unattributable claim.
    params: Dict[str, Any] = dc.field(default_factory=dict)
    # Why elaboration failed, when it did. A docs build must not fail because a
    # graph could not be built in the documentation environment (§0.4) -- the
    # page says so and carries on.
    error: str = ""
    elaborated: bool = True

    def to_dict(self):
        return {f.name: getattr(self, f.name) for f in dc.fields(self)}

    @property
    def ok(self) -> bool:
        return bool(self.dot) and not self.error


def build(task, pkg, loader, node_url=None, rundir=None) -> Elaborated:
    """Elaborate `task` and emit dot for the resulting graph.

    `node_url` is the U3 hook: `node -> str|None`, called per node. A hook that
    returns None or raises costs that node its link and nothing else.

    Any failure is captured rather than raised. Elaboration touches the
    filesystem and the environment, so it can fail for reasons that have
    nothing to do with the flow file being wrong -- and a page that says "could
    not elaborate here" is worth more than a build that stops.
    """
    name = getattr(task, 'name', '')
    out = Elaborated(task=name)

    try:
        from dv_flow.mgr.task_graph_builder import TaskGraphBuilder
        from dv_flow.mgr.task_graph_dot_writer import TaskGraphDotWriter
    except ImportError as e:
        out.error = "dv-flow-mgr does not provide the graph writer: %s" % e
        return out

    try:
        builder = TaskGraphBuilder(
            root_pkg=pkg,
            rundir=rundir or os.path.join(os.getcwd(), "rundir"),
            loader=loader)
        node = builder.mkTaskNode(name)
    except Exception as e:
        out.error = "could not elaborate %s: %s: %s" % (
            name, type(e).__name__, e)
        return out

    try:
        out.params = _resolved_params(builder, task)
    except Exception:
        # The graph is still worth showing without its parameter list; the
        # renderer will say the parameters are unknown rather than imply there
        # were none.
        out.params = {}

    try:
        import io
        writer = TaskGraphDotWriter()
        if node_url is not None and hasattr(writer, 'node_url'):
            writer.node_url = node_url
        # `write` takes a destination, not a return value. A StringIO keeps the
        # dot in memory: a docs build has no business writing files beside the
        # source tree.
        buf = io.StringIO()
        writer.write(node, buf)
        out.dot = buf.getvalue()
    except Exception as e:
        out.error = "could not render the graph for %s: %s: %s" % (
            name, type(e).__name__, e)

    return out


def _resolved_params(builder, task) -> Dict[str, Any]:
    values = builder.resolveTaskParams(task)
    return {k: str(v) for k, v in (values or {}).items()}


def supports_urls() -> bool:
    """Whether the installed dv-flow-mgr carries the U3 node-URL hook.

    Without it the diagram still renders; it just is not clickable. Checked so
    the renderer can say which of those a reader is looking at.
    """
    try:
        from dv_flow.mgr.task_graph_dot_writer import TaskGraphDotWriter
    except ImportError:
        return False
    return 'node_url' in {f.name for f in dc.fields(TaskGraphDotWriter)} \
        if dc.is_dataclass(TaskGraphDotWriter) else hasattr(
            TaskGraphDotWriter, 'node_url')

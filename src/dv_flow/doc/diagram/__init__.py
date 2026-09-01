"""Diagram *content*, as data.

A diagram is built as a `DiagramModel` and rendered separately. The split is
what makes diagram content golden-testable without producing a picture and
squinting at it -- "does the matrix body appear once" is a question about the
model, and answering it against rendered SVG would be answering a different,
harder question badly.
"""

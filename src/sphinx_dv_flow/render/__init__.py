"""Turning extraction documents into docutils nodes.

Nothing in here touches a `Task`. Everything it renders comes from a `TaskDoc`,
which is what makes the rendering testable against a document rather than
against a loaded project.
"""

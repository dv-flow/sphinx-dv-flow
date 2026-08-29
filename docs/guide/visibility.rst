###########################
Visibility Drives Inclusion
###########################

The engine's visibility model is already a documentation-audience model, and the
extension adopts it directly rather than inventing a second one.

============= ================================= ===================
Scope         Meaning                           Documented
============= ================================= ===================
``root``      Executable entry point            Yes — CLI page
``export``    Visible to other packages         Yes — library page
*(none)*      Package-internal                  Only ``:internal:``
``local``     Fragment-only                     Never
============= ================================= ===================

This is the single most useful thing the extension does. *What is published*
stops being a documentation decision and becomes a consequence of a declaration
the author already had to make — so the docs cannot drift from the interface,
because they are not a separate statement of it.

Why ``local`` is never included
===============================

``local`` is fragment-scoped: the name is not reachable from outside the
fragment that declares it. A page about one could not tell a reader anything
they could act on, so ``:internal:`` does not include them and no option does.

A task can be both
==================

A task declaring both ``root`` and ``export`` has two audiences: someone running
it, and someone composing with it. It gets the command-line view first, then a
*Using this task in a flow* section carrying the library blocks. Classification
picks one page template, so without this the second audience would simply
disappear.

Internal tasks
==============

.. code-block:: rst

    .. dvf:autopackage::
       :internal:

Reasonable for a document aimed at the project's own maintainers. It is off by
default because a task with no scope is, by the author's own declaration, not
part of what the package publishes.

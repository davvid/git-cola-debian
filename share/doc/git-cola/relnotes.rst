.. |beta(TM)| unicode:: beta U+2122

git-cola v1.4.2.3
=================
Usability, bells and whistles
-----------------------------
* Allow un/staging by right-clicking top-level items

  http://github.com/davvid/git-cola/issues/closed#issue/57

* Running 'commit' with no staged changes prompts to allow
  staging all files.

  http://github.com/davvid/git-cola/issues/closed#issue/55

* Fetch, Push, and Pull are now available via the menus

  http://github.com/davvid/git-cola/issues/closed#issue/58

Fixes
-----
* Simplified the actions widget to work around a regression
  in PyQt4 4.7.4.

  http://github.com/davvid/git-cola/issues/closed#issue/62

git-cola v1.4.2.2
=================
Usability, bells and whistles
-----------------------------
* `git-dag` |beta(TM)| interaction was made faster.

Fixes
-----
* Added '...' indicators to the buttons for
  'Fetch...', 'Push...', 'Pull...', and 'Stash...'.

  http://github.com/davvid/git-cola/issues/closed#issue/51

* Fixed a hang-on-exit bug in the cola-provided
  'ssh-askpass' implementation.

git-cola v1.4.2.1
=================
Usability, bells and whistles
-----------------------------
* Staging and unstaging is faster.

  http://github.com/davvid/git-cola/issues/closed#issue/48

* `git-dag` |beta(TM)| reads history in a background thread.

Portability
-----------
* Added :data:`cola.compat.hashlib` for `Python 2.4` compatibility
* Improved `PyQt 4.1.x` compatibility.

Fixes
-----
* Configured menu actions use ``sh -c`` for Windows portability.


git-cola v1.4.2
===============

Usability, bells and whistles
-----------------------------
* Added support for the configurable ``guitool.<tool>.*``
  actions as described in ``git-config(1)``.

  http://github.com/davvid/git-cola/issues/closed#issue/44

  http://www.kernel.org/pub/software/scm/git/docs/git-config.html

  This makes it possible to add new actions to `git-cola`
  by simply editing ``~/.gitconfig``.  This implements the
  same guitool support as `git-gui`.
* Introduced a stat cache to speed up `git-config` and
  repository status checks.
* Added Alt-key shortcuts to the main `git-cola` interface.
* The `Actions` dock widget switches between a horizontal
  and vertical layout when resized.
* We now use ``git diff --submodule`` for submodules
  (used when git >= 1.6.6).
* The context menu for modified submodules includes an option
  to launch `git-cola`.

  http://github.com/davvid/git-cola/issues/closed#issue/17

* Prefer ``$VISUAL`` over ``$EDITOR`` when both are defined.
  These are used to set a default editor in lieu of `core.editor`
  configuration.
* Force the editor to be ``gvim`` when we see ``vim``.
  This prevents us from launching an editor in the (typically
  unattached) parent terminal and creating zombie editors
  that cannot be easily killed.
* Selections are remembered and restored across updates.
  This makes the `partial-staging` workflow easier since the
  diff view will show the updated diff after staging.
* Show the path to the current repository in a tooltip
  over the commit message editor.

  http://github.com/davvid/git-cola/issues/closed#issue/45

* Log internal ``git`` commands when ``GIT_COLA_TRACE`` is defined.

  http://github.com/davvid/git-cola/issues/closed#issue/39

Fixes
-----
* Improved backwards compatibility for Python 2.4.
* `Review mode` can now review the current branch; it no longer
  requires you to checkout the branch into which the reviewed
  branch will be merged.
* Guard against `color.ui = always` configuration when using
  `git-log` by passing ``--no-color``.
* ``yes`` and ``no`` are now supported as valid booleans
  by the `git-config` parser.
* Better defaults are used for `fetch`, `push`, and `pull`..

  http://github.com/davvid/git-cola/issues/closed#issue/43

Packaging
---------
* Removed colon (`:`) from the applilcation name on Windows

  http://github.com/davvid/git-cola/issues/closed#issue/41

* Fixed bugs with the Windows installer

  http://github.com/davvid/git-cola/issues/closed#issue/40

* Added a more standard i18n infrastructure.  The install
  tree now has the common ``share/locale/$lang/LC_MESSAGES/git-cola.mo``
  layout in use by several projects.

* Started trying to accomodate Mac OSX 10.6 (Snow Leopard)
  in the ``darwin/`` build scripts but our tester is yet to
  report success building a `.app` bundle.

* Replaced use of ``perl`` in Sphinx/documentation Makefile
  with more-portable ``sed`` constructs.  Thanks to
  Stefan Naewe for discovering the portability issues and
  providing msysgit-friendly patches.

git-cola v1.4.1.2
=================

Usability, bells and whistles
-----------------------------
* It is now possible to checkout from the index as well
  as from `HEAD`.  This corresponds to the
  `Removed Unstaged Changes` action in the `Repository Status` tool.
* The `remote` dialogs (fetch, push, pull) are now slightly
  larger by default.
* Bookmarks can be selected when `git-cola` is run outside of a git repository.
* Added more user documentation.  We now include many links to
  external git resources.
* Added `git-dag Beta` to the available tools.
  `git-dag` is a node-based DAG history browser.
  It doesn't do much yet, but it's been merged so that we can start
  building and improving upon it.

Fixes
-----
* Fixed a missing ``import`` when showing `right-click` actions
  for unmerged files in the `Repository Status` tool.
* ``git update-index --refresh`` is no longer run everytime
  ``git cola version`` is run.
* Don't try to watch non-existant directories when using `inotify`.
* Use ``git rev-parse --symbolic-full-name`` plumbing to find
  the name of the current branch.

Packaging
---------
* The ``Makefile`` will now conditionally include a ``config.mak``
  file located at the root of the project.  This allows for user
  customizations such as changes to the `prefix` variable
  to be stored in a file so that custom settings do not need to
  be specified every time on the command-line.
* The build scripts no longer require a ``.git`` directory to
  generate the ``builtin_version.py`` module.  The release tarballs
  now include a ``version`` file at the root of the project which
  is used in lieu of having the git repository available.
  This allows for ``make clean && make`` to function outside of
  a git repository.
* Added maintainer's ``make dist`` target to the ``Makefile``.
* The built-in `simplejson` and `jsonpickle` libraries can be
  excluded from ``make install`` by specifying the ``standalone=true``
  `make` variable.  For example, ``make standalone=true install``.
  This corresponds to the ``--standalone`` option to ``setup.py``.


git-cola v1.4.1.1
=================

Usability, bells and whistles
-----------------------------
* We now use patience diff by default when it is available via
  `git diff --patience`.
* Allow closing the `cola classic` tool with `Ctrl+W`.

Fixes
-----
* Fixed an unbound variable error in the `push` dialog.

Packaging
---------
* Don't include `simplejson` in MANIFEST.in.
* Update desktop entry to read `Cola Git GUI`.


git-cola v1.4.1
===============

This feature release adds two new features directly from
`git-cola`'s github issues backlog.  On the developer
front, further work was done towards modularizing the code base.

Usability, bells and whistles
-----------------------------
* Dragging and dropping patches invokes `git-am`

  http://github.com/davvid/git-cola/issues/closed#issue/3

* A dialog to allow opening or cloning a repository
  is presented when `git-cola` is launched outside of a git repository.

  http://github.com/davvid/git-cola/issues/closed/#issue/22

* Warn when `push` is used to create a new branch

  http://github.com/davvid/git-cola/issues/closed#issue/35

* Optimized startup time by removing several calls to `git`.


Portability
-----------
* `git-cola` is once again compatible with PyQt 4.3.x.

Developer
---------
* `cola.gitcmds` was added to factor out git command-line utilities
* `cola.gitcfg` was added for interacting with `git-config`
* `cola.models.browser` was added to factor out repobrowser data
* Added more tests


git-cola v1.4.0.5
=================

Fixes
-----
* Fix launching external applications on Windows
* Ensure that the `amend` checkbox is unchecked when switching modes
* Update the status tree when amending commits


git-cola v1.4.0.4
=================

Packaging
---------
* Fix Lintian warnings


git-cola v1.4.0.3
=================

Fixes
-----
* Fix X11 warnings on application startup


git-cola v1.4.0.2
=================

Fixes
-----
* Added missing 'Exit Diff Mode' button for 'Diff Expression' mode

  http://github.com/davvid/git-cola/issues/closed/#issue/31

* Fix a bug when initializing fonts on Windows

  http://github.com/davvid/git-cola/issues/closed/#issue/32


git-cola v1.4.0.1
=================

Fixes
-----
* Keep entries in sorted order in the `cola classic` tool
* Fix staging untracked files

  http://github.com/davvid/git-cola/issues/closed/#issue/27

* Fix the `show` command in the Stash dialog

  http://github.com/davvid/git-cola/issues/closed/#issue/29

* Fix a typo when loading merge commit messages

  http://github.com/davvid/git-cola/issues/closed/#issue/30


git-cola v1.4.0
===============

This release focuses on a redesign of the git-cola user interface,
a tags interface, and better integration of the `cola classic` tool.
A flexible interface based on configurable docks is used to manage the
various cola widgets.

Usability, bells and whistles
-----------------------------
* New GUI is flexible and user-configurable
* Individual widgets can be detached and rearranged arbitrarily
* Add an interface for creating tags
* Provide a fallback `SSH_ASKPASS` implementation to prompt for
  SSH passwords on fetch/push/pull
* The commit message editor displays the current row/column and
  warns when lines get too long
* The `cola classic` tool displays upstream changes
* `git cola --classic` launches `cola classic` in standalone mode
* Provide more information in log messages

Fixes
-----
* Inherit the window manager's font settings
* Miscellaneous PyQt4 bug fixes and workarounds

Developer
---------
* Removed all usage of Qt Designer `.ui` files
* Simpler model/view architecture
* Selection is now shared across tools
* Centralized notifications are used to keep views in sync
* The `cola.git` command class was made thread-safe
* Less coupling between model and view actions
* The status view was rewritten to use the MVC architecture
* Added more documentation and tests


git-cola v1.3.9
===============

Usability, bells and whistles
-----------------------------
* Added a `cola classic` tool for browsing the entire repository
* Handle diff expressions with spaces
* Handle renamed files

Portability
-----------
* Handle carat `^` characters in diff expressions on Windows
* Worked around a PyQt 4.5/4.6 QThreadPool bug

Documentation
-------------
* Added a keyboard shortcuts reference page
* Added developer API documentation

Fixes
-----
* Fix the diff expression used when reviewing branches
* Fix a bug when pushing branches
* Fix X11 warnings at startup
* Fix more interrupted system calls on Mac OS X


git-cola v1.3.8
===============

Usability, bells and whistles
-----------------------------
* Fresh and tasty SVG logos
* Added `Branch Review` mode for reviewing topic branches
* Added diff modes for diffing between tags, branches,
  or arbitrary `git diff` expressions
* The push dialog selects the current branch by default.
  This is in preparation for `git-1.7.0` where unconfigured `git push`
  will refuse to push when run without specifying the remote name
  and branch.  See the `git` release notes for more information
* Support `open` and `clone` commands on Windows
* Allow saving cola UI layouts
* Re-enabled `double-click-to-stage` for unmerged entries.
  Disabling it for unmerged items was inconsistent, though safer.
* Show diffs when navigating the status tree with the keyboard

Packaging
---------
* Worked around `pyuic4` bugs in the `setup.py` build script
* Added Mac OSX application bundles to the download page


git-cola v1.3.7
===============

Subsystems
----------
* `git-difftool` became an official git command in `git-1.6.3`.
* `git-difftool` learned `--no-prompt` / `-y` and a corresponding
  `difftool.prompt` configuration variable

Usability, bells and whistles
-----------------------------
* Warn when `non-fast-forward` is used with fetch, push or pull
* Allow `Ctrl+C` to exit cola when run from the command line

Fixes
-----
* Support Unicode font names
* Handle interrupted system calls

Developer
---------
* `PEP-8`-ified more of the cola code base
* Added more tests

Packaging
---------
* All resources are now installed into `$prefix/share/git-cola`.
  Closed Debian bug #519972

  http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=519972


git-cola v1.3.6
===============

Subsystems
----------
* Added support for Kompare in `git-difftool`
* Added a separate configuration namespace for `git-difftool`
* Added the `diff.tool` configuration variable to define the default diff tool

Usability, bells and whistles
-----------------------------
* The stash dialog allows passing the `--keep-index` option to `git stash`
* Amending a published commit warns at commit time
* Simplified the file-across-revisions comparison dialog
* `origin` is selected by default in fetch/push/pull
* Removed the search field from the log widget
* The log window moved into a drawer widget at the bottom of the UI
* Log window display can be configured with
  `cola.showoutput` = `{never, always, errors}`.  `errors` is the default.
* `NOTE` -- `cola.showoutput` was removed with the GUI rewrite in 1.4.0.

Developer
---------
* Improved nose unittest usage

Packaging
---------
* Added a Windows/msysGit installer
* Included private versions of `simplejson` and `jsonpickle`
  for ease of installation and development

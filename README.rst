=================
githubsimple-trac
=================

This is a simplified version of the Trac/Github integration plugin
http://github.com/davglass/github-trac

Many features and most dependencies are stripped, leaving only the browser/ and changeset/
redirects.


Installation
============

This plugin allows you to replace the builtin Trac browser with redirects to the GitHub source browser.

To install this Trac Plugin:

    1. Clone the repository::

        git clone git://github.com/pv/githubsimple-trac.git

    2. Install the Plugin::

        cd githubsimple-trac
        sudo python setup.py install   # ... or something similar

    3. Configure Trac by editing your ``trac.ini``::

        [components]
        githubsimple.* = enabled

        [githubsimple]
        browser = http://github.com/davglass/tree/master    # your Github URL
        suppress_changesets = true
        local_repo = /path/to/local/repo          # optional
	secret_token = somesecretword             # optional

    4. (Optional) Clone your Git repo to some path in your Trac server,
       if you specified ``local_repo``

    5. (Optional) Configure Github Post-Receive URL to::

        http://your.trac.domain/someproject/github/somesecretword

       where ``somesecretwork`` should match what's in ``trac.ini``.
       This will only invoke ``git fetch`` on the ``local_repo``
       so that the timeline view stays up to date.

    6. All done.


Code Browser
============

The code browser portion of the plugin is designed to replace the code browser
built into Trac with a simple redirect to the GitHub source browser.

Note that this will not make the commits appear in the timeline etc. You need
the GitPlugin to do that: http://trac-hacks.org/wiki/GitPlugin

Also, if you want that, consider using the full github-trac plugin.


Changesets
==========

This plugin intercepts the /changeset url, which allows using::

    git:98d9ffe2

    commit:98d9ffe2

syntax in referring to Git commits.

It tries to automatically detect if the commit is a valid SVN revision number,
and in that case points it to Trac's builtin source browser instead of Github.
(May be useful for projects converted from SVN...)

Timeline
========

You can set the ``suppress_changesets`` option to suppress SVN changesets in
the Timeline view.


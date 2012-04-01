import sys
import os
import re
import cgi
import urllib
import datetime
import subprocess
from trac.util.datefmt import utc
from trac.core import *
from trac.config import Option, IntOption, ListOption, BoolOption
from trac.web.api import IRequestFilter, IRequestHandler, Href
from trac.wiki.api import IWikiSyntaxProvider
from trac.timeline.api import ITimelineEventProvider
from trac.util.translation import _
from genshi.builder import tag

class GithubSimplePlugin(Component):
    implements(IRequestHandler, IRequestFilter, IWikiSyntaxProvider, ITimelineEventProvider)

    browser = Option('githubsimple', 'browser', '',
        doc=("Place your GitHub Source Browser URL here to have "
             "the /browser entry point redirect to GitHub."))
    suppress_changesets = BoolOption('githubsimple', 'suppress_changesets',
        False, doc="Suppress SVN changesets in the timeline view")
    local_repo = Option('githubsimple', 'local_repo', '',
        doc="Path to local repository")
    secret_token = Option('githubsimple', 'secret_token', '',
        doc="Secret token in the post-receive URL")

    def __init__(self):
        self.env.log.debug("Browser: %s" % self.browser)
        if self.local_repo:
            self.repo = GitRepo(self.local_repo)
        else:
            self.repo = None
        self.process_hook = False
        if self.suppress_changesets:
            monkeypatch_trac_timeline()

    #--------------------------------------------------------------------------
    # ITimelineEventProvider methods
    #--------------------------------------------------------------------------

    def get_timeline_filters(self, req):
        if 'CHANGESET_VIEW' in req.perm:
            return [('changeset', _('Changesets'))]
        else:
            return []

    def get_timeline_events(self, req, start, stop, filters):
        if 'changeset' not in filters:
            return
        if not self.repo:
            yield ('changeset', datetime.datetime.now(utc), '',
                   ("master-commits", 'See Git commit log'), self)
            return

        for rev, committer, author, date, subject in self.repo.log(start, stop):
            if author != committer:
                author = "%s [%s]" % (author, committer)
            yield ('changeset', date, author, (rev[:8], subject), self)

    def render_timeline_event(self, context, field, event):
        kind, date, author, data, provider = event
        rev, message = data

        if field == 'url':
            return context.href.changeset(rev)
        elif field == 'description':
            return message
        elif field == 'title':
            title = tag(_("Commit "), tag.em('[%s]' % rev))
            return title
        else:
            raise NotImplementedError()

    #--------------------------------------------------------------------------
    # IRequestHandler methods
    #--------------------------------------------------------------------------

    def match_request(self, req):
        serve = (req.path_info.rstrip('/') == ('/github/%s' % self.secret_token)
                 and req.method == 'POST'
                 and self.secret_token)
        if serve:
            self.process_hook = True
            # This is hacky but it's the only way I found to let Trac
            # post to this request without a valid form_token
            req.form_token = None

        self.env.log.debug("Handle Request: %s" % serve)
        return serve

    def pre_process_request(self, req, handler):
        # This has to be done via the pre_process_request handler
        # Seems that the /browser request doesn't get routed to match_request :(
        if self.browser:
            serve = req.path_info.startswith('/browser') \
                        and not is_svn_rev(req.args.get('rev'))
            self.env.log.debug("Handle Pre-Request /browser: %s" % serve)
            if serve:
                self.process_browser_url(req)

            serve2 = req.path_info.startswith('/changeset') \
                        and not is_svn_changeset_request(req.path_info)
            self.env.log.debug("Handle Pre-Request /changeset: %s" % serve2)
            if serve2:
                self.process_changeset_url(req)
        return handler

    def process_request(self, req):
        if self.process_hook:
            self.process_commit_post(req)

    def post_process_request(self, req, template, data, content_type):
        return (template, data, content_type)

    #--------------------------------------------------------------------------
    # Request processing hooks
    #--------------------------------------------------------------------------

    def process_changeset_url(self, req):
        self.env.log.debug("process_changeset_url")
        browser = self.browser.replace('/tree/master', '/commit/')
        
        url = req.path_info.replace('/changeset/', '')
        if not url:
            browser = self.browser
            url = ''
        if url.endswith('-commits'):
            url = url[:-8]
            browser = browser.replace('/commit/', '/commits/')

        redirect = '%s%s' % (browser, url)
        self.env.log.debug("Redirect URL: %s" % redirect)
        out = 'Going to GitHub: %s' % redirect

        req.redirect(redirect)

    def process_browser_url(self, req):
        self.env.log.debug("process_browser_url")
        browser = self.browser.replace('/master', '/')
        rev = req.args.get('rev')

        url = req.path_info.replace('/browser', '')
        if not rev:
            rev = ''
        url = url.replace('/trunk', '/master')
        if url.startswith('/'):
            url = url[1:]

        redirect = '%s%s%s' % (browser, rev, url)
        self.env.log.debug("Redirect URL: %s" % redirect)
        out = 'Going to GitHub: %s' % redirect

        req.redirect(redirect)

    def process_commit_post(self, req):
        data = req.args.get('payload')
        if self.repo:
            self.repo.fetch()
        req.redirect("/")

    #--------------------------------------------------------------------------
    # IWikiSyntaxProvider methods
    #--------------------------------------------------------------------------

    def get_wiki_syntax(self):
        return []

    def get_link_resolvers(self):
        browser = self.browser.replace('/tree/master', '/commit/')
        def fmt(formatter, ns, target, label):
            if not label:
                label = cgi.escape(target)
            target = urllib.quote(target)
            return '<a href="%s%s">%s</a>' % ( browser, target, label)

        return [('git', fmt), ('commit', fmt)]


#------------------------------------------------------------------------------
# Helper routines
#------------------------------------------------------------------------------

def is_svn_rev(rev):
    try:
        revno = int(rev)
    except (TypeError, ValueError):
        return False
    if revno > 100000:
        return False
    return True

def is_svn_changeset_request(path_info):
    m = re.match('^/changeset/([^/]+).*?', path_info)
    if m:
        return is_svn_rev(m.group(1))
    return False

def monkeypatch_trac_timeline():
    def get_timeline_events(self, req, start, stop, filters):
        return []
    import trac.versioncontrol.web_ui.changeset
    trac.versioncontrol.web_ui.changeset.ChangesetModule.get_timeline_events \
        = get_timeline_events

class GitRepo(object):
    def __init__(self, repo):
        self.repo = repo

    def _git(self, *cmd):
        cwd = os.getcwd()
        try:
            os.chdir(self.repo)
            p = subprocess.Popen(['git'] + list(cmd),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out, err = p.communicate()
            return out
        finally:
            os.chdir(cwd)

    def log(self, start, end):
        """
        Generator yielding (hash, committer, author, commit_datetime,
                            subject), ...
        """
        fmt_sep = '\x08'
        fmt = ['%H', '%P', '%cn', '%an', '%ct', '%s']
        cmd = ['log', '-100', '--all',
               '--pretty=format:' + fmt_sep.join(fmt)]
        if start:
            cmd.append(start.strftime('--since=%Y-%m-%d %H:%M:%S'))
        if end:
            cmd.append(end.strftime('--until=%Y-%m-%d %H:%M:%S'))

        desc_re = re.compile(r'\s*\((.*)\)\s*', re.S)
        branches = {}

        # Read refs
        out = self._git('show-ref')
        for entry in out.splitlines():
            parts = entry.split()
            if len(parts) == 2:
                commit, ref = parts
                if ref.startswith('refs/heads/'):
                    ref = ref[11:]
                elif ref.startswith('refs/remotes/origin/'):
                    ref = ref[20:]
                else:
                    continue
                ref = ref.strip()
                if not ref or ref == 'HEAD':
                    continue
                branches.setdefault(commit, set()).add(ref)

        # Read log
        out = self._git(*cmd)
        for entry in out.splitlines():
            parts = entry.split(fmt_sep)
            if len(parts) == len(fmt):
                commit, parents, committer, author, stamp, subject = parts

                # Format timestamp
                try:
                    stamp = datetime.datetime.fromtimestamp(int(stamp), utc)
                except ValueError:
                    continue

                # Trace branches (in cases where it can be done cheaply)
                refs = branches.get(commit, None)
                if refs:
                    for parent in parents.split():
                        # tag parents with current branch names
                        branches.setdefault(parent, set()).update(refs)

                # Add branch names to subject
                if refs:
                    subject = "[%s] %s" % (", ".join(sorted(refs)), subject)

                # Send forward
                yield (commit, committer, author, stamp, subject)

    def fetch(self):
        self._git('fetch')


#------------------------------------------------------------------------------
# Communicating with Git
#------------------------------------------------------------------------------

class Cmd(object):
    executable = None

    def __init__(self, executable):
        self.executable = executable

    def _call(self, command, args, kw, repository=None, call=False):
        cmd = [self.executable, command] + list(args)
        cwd = None

        if repository is not None:
            cwd = os.getcwd()
            os.chdir(repository)

        try:
            if call:
                return subprocess.call(cmd, **kw)
            else:
                return subprocess.Popen(cmd, **kw)
        finally:
            if cwd is not None:
                os.chdir(cwd)

    def __call__(self, command, *a, **kw):
        ret = self._call(command, a, {}, call=True, **kw)
        if ret != 0:
            raise RuntimeError("%s failed" % self.executable)

    def pipe(self, command, *a, **kw):
        stdin = kw.pop('stdin', None)
        p = self._call(command, a, dict(stdin=stdin, stdout=subprocess.PIPE),
                      call=False, **kw)
        return p.stdout

    def read(self, command, *a, **kw):
        p = self._call(command, a, dict(stdout=subprocess.PIPE),
                      call=False, **kw)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError("%s failed" % self.executable)
        return out

    def readlines(self, command, *a, **kw):
        out = self.read(command, *a, **kw)
        return out.rstrip("\n").split("\n")

    def test(self, command, *a, **kw):
        ret = self._call(command, a, dict(stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE),
                        call=True, **kw)
        return (ret == 0)

git = Cmd("git")

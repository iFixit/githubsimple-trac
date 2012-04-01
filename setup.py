import os
import subprocess
from setuptools import find_packages, setup

version = "0.1.1.dev"

# Return the git revision as a string
def git(*args):
    # construct minimal environment (LANGUAGE is used on win32)
    env = {'LANGUAGE': 'C', 'LANG': 'C', 'LC_ALL': 'C'}
    for k in ['SYSTEMROOT', 'PATH']:
        v = os.environ.get(k)
        if v is not None:
            env[k] = v
    p = subprocess.Popen(['git'] + list(args),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=env)
    out, err = p.communicate()
    if p.returncode != 0:
        return None
    return out

def git_version(base_version):
    try:
        out = git('rev-parse', 'HEAD')
        rev = out.strip().decode('ascii').encode('ascii')
        tag = git('describe', '--tags', '--exact-match', 'HEAD')
    except OSError:
        rev = u"unknown"
        tag = None

    if tag is not None:
        if tag == base_version:
            return base_version
        else:
            raise RuntimeError("Git tag does not match version number!")

    if base_version.endswith('dev'):
        return base_version + "." + rev[:6]

version = git_version(version)

# Run distutils
setup(
    name='GithubSimplePlugin',
    version=version,
    author='Pauli Virtanen, Dav Glass',
    author_email='pav@iki.fi',
    description = "Redirects Trac /browser and /changeset urls to github.com",
    license = "BSD",
    url = "http://github.com/pv/githubsimple-trac",
    packages = find_packages(exclude=['*.tests*']),
    package_data={'githubsimple' : []},
    install_requires = [],
    entry_points = {
        'trac.plugins': [
            'githubsimple = githubsimple',
        ]    
    }
)

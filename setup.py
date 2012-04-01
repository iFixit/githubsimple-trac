from setuptools import find_packages, setup

setup(
    name='GithubSimplePlugin',
    version='0.1.1',
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

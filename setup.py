import re
from setuptools import setup


def find_version(filename):
    _version_re = re.compile(r"__version__ = ['\"](.*)['\"]")
    last = None  # match python semantics
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            last = version_match.group(1)

    return last


__version__ = find_version('idlib/__init__.py')

with open('README.md', 'rt') as f:
    long_description = f.read()

org_require = ['beautifulsoup4[html5lib]']
rdf_require = ['pyontutils>=0.1.28']
oauth_require = ['google-auth-oauthlib']
tests_require = (['pytest', 'joblib>=1.1.0'] +
                 org_require +
                 rdf_require +
                 oauth_require)
setup(name='idlib',
      version=__version__,
      description='A library for working with identifiers of all kinds.',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/tgbugs/idlib',
      author='Tom Gillespie',
      author_email='tgbugs@gmail.com',
      license='MIT',
      classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy',
          'Operating System :: POSIX :: Linux',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
      ],
      keywords=('python persistent identifiers'),
      packages=[
          'idlib',
          'idlib.apis',
          'idlib.conventions',
          'idlib.formats',
          'idlib.systems',
      ],
      python_requires='>=3.6',
      tests_require=tests_require,
      install_requires=['orthauth[yaml,sxpr]>=0.0.13', 'requests'],
      extras_require={'test': tests_require,
                      'org': org_require,
                      'rdf': rdf_require,
                      'oauth': oauth_require,
                     },
      scripts=[],
      entry_points={'console_scripts': [ ],},
     )

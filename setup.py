import re
from setuptools import setup


def find_version(filename):
    _version_re = re.compile(r"__version__ = '(.*)'")
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)


__version__ = find_version('idlib/__init__.py')

with open('README.md', 'rt') as f:
    long_description = f.read()

rdf_require = ['neurdflib>=5.0.1', 'pyontutils>=0.1.13']
tests_require = ['pytest', 'pytest-runner'] + rdf_require
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
      ],
      keywords=('python persistent identifiers'),
      packages=[
          'idlib',
          'idlib.conventions',
          'idlib.formats',
          'idlib.systems',
      ],
      python_requires='>=3.6',
      tests_require=tests_require,
      install_requires=['requests'],
      extras_require={'test': tests_require,
                      'rdf': rdf_require,
                     },
      scripts=[],
      entry_points={'console_scripts': [ ],},
     )

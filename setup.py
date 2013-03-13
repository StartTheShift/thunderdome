import sys
from setuptools import setup, find_packages

#next time:
#python setup.py register
#python setup.py sdist upload

version = open('thunderdome/VERSION', 'r').readline().strip()

long_desc = """
thunderdome is an Object-Graph Mapper (OGM) for Python

[Documentation](https://thunderdome.readthedocs.org/en/latest/)

[Report a Bug](https://github.com/StartTheShift/thunderdome/issues)

[Users Mailing List](https://groups.google.com/forum/#!forum/thunderdome-users)
"""

setup(
    name='thunderdome',
    version=version,
    description='Titan Object-Graph Mapper (OGM)',
    dependency_links=['https://github.com/StartTheShift/thunderdome/archive/{0}.tar.gz#egg=thunderdome-{0}'.format(version)],
    long_description=long_desc,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Environment :: Plugins",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='cassandra,titan,ogm,thunderdome',
    install_requires=['pyparsing==1.5.7'],
    author='StartTheShift',
    author_email='dev@shift.com',
    url='https://github.com/StartTheShift/thunderdome',
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
)

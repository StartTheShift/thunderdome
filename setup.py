from setuptools import setup, find_packages

#next time:
#python setup.py register
#python setup.py sdist upload

version = '0.0.8'

long_desc = """
thunderdome is a Cassandra CQL ORM for Python in the style of the Django orm and mongoengine

[Documentation](https://thunderdome.readthedocs.org/en/latest/)

[Report a Bug](https://github.com/bdeggleston/thunderdome/issues)

[Users Mailing List](https://groups.google.com/forum/?fromgroups#!forum/thunderdome-users)

[Dev Mailing List](https://groups.google.com/forum/?fromgroups#!forum/thunderdome-dev)

**NOTE: thunderdome is in alpha and under development, some features may change. Make sure to check the changelog and test your app before upgrading**
"""

setup(
    name='thunderdome',
    version=version,
    description='Cassandra CQL ORM for Python in the style of the Django orm and mongoengine',
    dependency_links = ['https://github.com/bdeggleston/thunderdome/archive/{0}.tar.gz#egg=thunderdome-{0}'.format(version)],
    long_description=long_desc,
    classifiers = [
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
    keywords='cassandra,cql,orm',
    install_requires = ['cql'],
    author='Blake Eggleston',
    author_email='bdeggleston@gmail.com',
    url='https://github.com/bdeggleston/thunderdome',
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
)


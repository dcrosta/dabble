from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

from dabble import __version__

setup(
    name='dabble',
    version=__version__,
    description='Simple A/B testing framework',
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.4",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    author='Daniel Crosta',
    author_email='dcrosta@late.am',
    url='https://github.com/dcrosta/dabble',
    keywords='python web abtest split ab a/b test',
    packages=find_packages(),
)


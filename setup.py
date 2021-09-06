import sys
from importlib.machinery import SourceFileLoader

from setuptools import find_packages, setup


def load_version(filename):
    loader = SourceFileLoader(filename, filename)
    return loader.load_module().VERSION


def load_requirements(filename):
    with open(filename) as fd:
        return fd.readlines()


requirements = load_requirements("requirements.txt")
test_requirements = load_requirements("requirements-dev.txt")

package_data = {'juicefs.lib': ['libjfs.so', 'juicefs']}
if sys.platform == 'win32':
    package_data = {'juicefs.lib': ['libjfs.dll', 'juicefs.exe']}

setup(
    name="juicefs",
    description="JuiceFS Python SDK",
    version=load_version("juicefs/version.py"),
    author="r-eng",
    author_email="r-eng@megvii.com",
    url="https://github.com/megvii-research/juicefs-python",
    packages=find_packages(exclude=("tests",)),
    package_data=package_data,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',  # noqa
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development',
        'Topic :: Utilities'
    ],
    tests_require=test_requirements,
    install_requires=requirements,
    python_requires=">=3.5",
)

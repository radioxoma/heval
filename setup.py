from os import path

from setuptools import find_packages, setup

import heval

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="heval",
    version=heval.__version__,
    description="Medical calculator for intensive care unit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/radioxoma/heval/",
    author="Eugene Dvoretsky",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Medical Science Apps",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
    ],
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    python_requires=">=3.8.*, <4",
    entry_points={
        "gui_scripts": [
            "heval=heval.__main__:main",
        ]
    },
)

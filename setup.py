from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='heval',
    version='0.0.1',
    description='Heval - a human evaluator',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/radioxoma/heval/',
    author='Eugene Dvoretsky',
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Medical Science Apps',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    python_requires='>=3.4.*, <4',
    entry_points={
        'gui_scripts': [
            'heval=heval.main:main',
        ]
    }
)

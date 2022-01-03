#!/usr/bin/env python
from setuptools import setup, find_packages

from deploy import find_version, read

COMMANDS = ["databrowser", "esgf", "history", "plugin", "crawl-my-data"]

setup(name="evaluation_system",
      version=find_version("src/evaluation_system", "__init__.py"),
      author="German Climate Computing Centre (DKRZ)",
      maintainer="Climate Informatics and Technology (CLINT)",
      description="Free Evaluation and Analysis Framework (Freva) ",
      long_description=read("README.md"),
      long_description_content_type='text/markdown',
      license="BSD-3-Clause",
      packages=find_packages('src'),
      package_dir={"": "src"},
      install_requires=["argcomplete",
                        "Django",
                        "humanize",
                        "mysqlclient",
                        "numpy",
                        "python-git",
                        "pymysql",
                        "pandas",
                        "Pillow",
                        "PyPDF2"],
      extras_require={
        "docs": [
              "sphinx",
              "nbsphinx",
              "recommonmark",
              "ipython",  # For nbsphinx syntax highlighting
              "sphinxcontrib_github_alt",
              ],
        "test": [
              "pytest",
              "nbformat",
              "pytest-html",
              "pytest-env",
              "pytest-cov",
              "nbval",
              "h5netcdf",
              "mock",
              "requests_mock",
              "allure-pytest",
              "python-swiftclient",
              "testpath",
          ]
        },
      entry_points={"console_scripts": [
          "freva = freva.cli:main"]+[
              f"freva-{cmd} = freva.cli.{cmd.replace('-', '_')}:main" for cmd in COMMANDS
              ]
      },
      python_requires='>=3.8',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Topic :: Scientific/Engineering :: Data Analysis',
          'Topic :: Scientific/Engineering :: Earth Sciences',
      ]
      )

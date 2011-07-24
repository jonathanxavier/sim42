#!/usr/bin/env python
"""Setup file for the distribution of PyCrust. PyCrust is a pure
Python distribution. Thanks to Andy Todd, who created the original
setup.py for PyCrust."""

__author__ = "Patrick K. O'Brien <pobrien@orbtech.com>"
__cvsid__ = "$Id: setup.py,v 1.2 2002/08/31 05:10:24 raul Exp $"
__revision__ = "$Revision: 1.2 $"[11:-2]

from distutils.core import setup
import version
import glob

setup(name="PyCrust",
      version=str(version.VERSION),
      description="PyCrust - The Flakiest Python Shell",
      author="Patrick K. O'Brien",
      author_email="pobrien@orbtech.com",
      url="http://sourceforge.net/projects/pycrust/",
      packages=["PyCrust"],
      package_dir={"PyCrust": "."},
      long_description="""
      PyCrust is an interactive Python environment written in Python.
      PyCrust components can run standalone or be integrated into other
      development environments and/or other Python applications.

      PyCrust comes with an interactive Python shell (PyShell), an 
      interactive namespace/object tree control (PyFilling) and an 
      integrated, split-window combination of the two (PyCrust).
      """,
      data_files=[("PyCrust", ["PyCrust.ico",]),
                  ("PyCrust/Data", glob.glob("Data/*.py")),
                  ("PyCrust/Demos", glob.glob("Demos/*.py")),
                  ("PyCrust/Docs", glob.glob("Docs/*.txt")),
                  ("PyCrust/tests", glob.glob("tests/*.py")),
                 ],
     )

 

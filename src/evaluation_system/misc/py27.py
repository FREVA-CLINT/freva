"""
Created on 22.03.2013

@author: estani

Classes available after 2.7 to make it run also for 2.6
"""

try:
    import collections
    OrderedDict = collections.OrderedDict
except:  # pragma: no cover
    raise Exception, 'Python 2.6 is not longer supported!'

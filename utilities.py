import yaml
import pprint
"""Utility functions for debugging"""

def printSlice(objectsList, fieldName):
    for myobject in objectsList:
        try:
            print(pprint.pprint(myobject[fieldName]))
        except KeyError:
            pass

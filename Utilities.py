#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: Utilities.py
Author: John DeMastri
Create Date: 2025-05-01
Version: 0.1
Description: Placeholder for general-purpose functions and code.

License: MIT License
Contact: chess@demastri.com
"""
import sys

def getOptionFromList(i, paramName, optList ):
    if i >= len(sys.argv):
        print("- No argument provided for "+paramName+".  Exiting.")
        return None
    thisParam = sys.argv[i].lower()
    if thisParam not in optList:
        print("- Invalid argument <" + thisParam + "> provided for "+paramName+".  Exiting.")
        return None
    print("- Setting "+paramName+" to <" + thisParam + ">")
    return optList.index(thisParam)

def getOpenOption(i, paramName):
    if i >= len(sys.argv):
        print("- No argument provided for " + paramName + ".  Exiting.")
        return None
    thisParam = sys.argv[i]
    print("- Setting " + paramName + " to <" + thisParam + ">")
    return thisParam

def is_integer(str_val):
    try:
        int(str_val)
        return True
    except ValueError:
        return False

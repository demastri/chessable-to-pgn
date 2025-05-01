#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: CommandLine.py
Author: John DeMastri
Create Date: 2025-05-01
Version: 0.3
Description: Tools to extract command line parameters and set processing modes for the application.
Also has tools to get commands for interactive mode.

License: MIT License
Contact: chess@demastri.com
"""

import sys
import Utilities
import ConfigData
from WebFetch import WebFetch
from Pgn import Pgn

def processCommandLineParams():
    # there really just end up being two operational parameters
    # - webFetchMode = All (overwrite), None (Use Existing), Update (Use Existing, Get the Rest)
    # - pgnMode - No (don't generate), Incremental (after getting a variation, do Pgn), After (after getting all vars, do Pgn)
    # there are two arguments
    # - list of courses - get the course, get all chapters, then all variations for each course in course and course/variations
    # - list of variations - get the listed variations, and place in one-off/variations
    # there are a few environmental parameters
    # - set html root
    # - set pgn root
    # - set browser binary path
    # - set browser profile dir
    # - set browser profile name

    # set defaults
    WebFetch.doFetch = WebFetch.FETCH_NEW
    Pgn.doPgn = Pgn.PGN_INCREMENTAL

    i = 0
    inCourse = False
    inVariation = False
    courses = []
    variations = []
    processMode = "batch"

    while i + 1 < len(sys.argv):
        i += 1
        thisArg = sys.argv[i].lower()
        argIsInt = Utilities.is_integer(thisArg)

        # check courses
        if inCourse and argIsInt:
            courses.append(thisArg)
            continue
        if thisArg == "-courses":
            inCourse = True
            inVariation = False
            continue

        # check variations
        if inVariation and argIsInt:
            variations.append(thisArg)
            continue
        if thisArg == "-variations":
            inCourse = False
            inVariation = True
            continue

        # check operational parameters
        if thisArg == "-interactive":
            processMode = "interactive"
            continue

        if thisArg == "-batch":
            processMode = "batch"
            continue

        # check operational parameters
        if thisArg == "-web":
            i = i + 1  # the value of this parameter is the next arg
            WebFetch.doFetch = Utilities.getOptionFromList(i, "web mode", WebFetch.flagNames)
            if WebFetch.doFetch is None:
                return None, None, None
            continue

        if thisArg == "-pgn":
            i = i + 1  # the value of this parameter is the next arg
            Pgn.doPgn = Utilities.getOptionFromList(i, "pgn mode", Pgn.flagNames)
            if Pgn.doPgn is None:
                return None, None, None
            continue

        # check environmental parameters
        if thisArg == "-pgnroot":
            i = i + 1  # the value of this parameter is the next arg
            ConfigData.PGN_CACHE_PATH = Utilities.getOpenOption(i, "pgn root location")
            if ConfigData.PGN_CACHE_PATH is None:
                return None, None, None
            continue

        if thisArg == "-htmlroot":
            i = i + 1  # the value of this parameter is the next arg
            ConfigData.HTML_CACHE_PATH = Utilities.getOpenOption(i, "html root location")
            if ConfigData.HTML_CACHE_PATH is None:
                return None, None, None
            continue

        if thisArg == "-browserbinary":
            i = i + 1  # the value of this parameter is the next arg
            ConfigData.CHROME_FOR_TESTING_BINARY_LOC = Utilities.getOpenOption(i, "browser binary location")
            if ConfigData.CHROME_FOR_TESTING_BINARY_LOC is None:
                return None, None, None
            continue

        if thisArg == "-browserprofiledir":
            i = i + 1  # the value of this parameter is the next arg
            ConfigData.TESTING_PROFILE_BASE_DIR = Utilities.getOpenOption(i, "browser profile root location")
            if ConfigData.TESTING_PROFILE_BASE_DIR is None:
                return None, None, None
            continue

        if thisArg == "-browserprofile":
            i = i + 1  # the value of this parameter is the next arg
            ConfigData.TESTING_PROFILE = Utilities.getOpenOption(i, "browser profile to use")
            if ConfigData.TESTING_PROFILE is None:
                return None, None, None
            continue

        print("- Don't know how to apply command line argument <" + thisArg + ">")

    return processMode, courses, variations

def getNextItemToProcess():
    srcChoices = ["q", "c", "v"]
    cOut = []
    vOut = []

    s = ""
    while s not in srcChoices:
        s = input("- Enter 'c' for course, 'v' for variation, 'q' to quit: ")
        if s == "":
            s = "c"
        if s == "q":
            return True, None, None
        if s == "c":
            c = input("-- Enter the course ID: ")
            cOut.append(c)
        if s == "v":
            v = input("-- Enter the variation ID: ")
            vOut.append(v)

    s = "-1"
    while not Utilities.is_integer(s) or int(s) not in range(len(WebFetch.flagNames)):
        s = input( "--- HTML - Fetch New HTML (1-default), refetch All HTML (2), use existing HTML (3), or quit (q)? ")
        if s == "q":
            return True, None, None
        # real range of values is 0-2, so have to use s-1
        WebFetch.doFetch = WebFetch.FETCH_NEW if s == "-1" or not Utilities.is_integer(s) else int(s)-1
        s = str(WebFetch.doFetch)
    print( "-- Web fetch mode set to "+WebFetch.flagNames[WebFetch.doFetch])

    s = "-1"
    while not Utilities.is_integer(s) or int(s) not in range(len(Pgn.flagNames)):
        s = input("--- Write PGN - Don't (1), During HTML Processing (2-default), After HTML Processing (3), or quit (q)? ")
        if s == "q":
            return True, None, None
        # real range of values is 0-2, so have to use s-1
        Pgn.doPgn = Pgn.PGN_INCREMENTAL if s == "-1" or not Utilities.is_integer(s) else int(s)-1
        s = str(Pgn.doPgn)
    print( "-- PGN write mode set to "+Pgn.flagNames[Pgn.doPgn])

    return False, cOut, vOut




#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: chessable-tp-pgn.py
Author: John DeMastri
Create Date: 2025-04-27
Version: 0.3
Description: Entry point and main workflow driver for the applicaftion

License: MIT License
Contact: chess@demastri.com
"""

from datetime import datetime

from bs4 import BeautifulSoup

import CommandLine
from WebFetch import WebFetch
from Pgn import Pgn

profileIds = []


def main():
    print("Chessable-to-PGN tool (c) 2025 John DeMastri")

    print("--- starting ---")
    print(datetime.now())
    processMode, courses, variations = CommandLine.processCommandLineParams()
    if courses is None:
        print("- Could not process command line parameters.  Exiting...")
        return

    if processMode == "interactive":
        quit = False
        while not quit:
            quit, courseId, variationId = CommandLine.getNextItemToProcess()
            # htmlOption: 1 = fetch new, 2 = fetch all, 3 = use existing (don't fetch)
            if not quit:
                processBatch(courseId, variationId)
                print("--- HTML: " + WebFetch.flagNames[WebFetch.doFetch] + " fetched\n--- PGN: " + Pgn.flagNames[
                    Pgn.doPgn] + " written")
    elif processMode == "batch":
        processBatch(courses, variations)
    else:
        print("unknown process mode <" + processMode + ">")

    print("--- complete ---")
    print(datetime.now())
    if processMode == "interactive":
        input("Exiting interactive mode!  Press ENTER to close this window.")


def processBatch(courses, variations):
    for courseId in courses:
        print("--- Processing course " + courseId + " fetch: " + WebFetch.flagNames[WebFetch.doFetch] + " pgn: " +
              Pgn.flagNames[Pgn.doPgn])
        # print("--- getting variation html ---")
        courseBS, chapters = loadCourseInfo(courseId)
        # this first pass loads/saves all of the chapter htmls
        # running single-threaded - an hour trying to get threading and processing failed (selenium issues)
        print("----------")

        chapterResults = loadChapterInfo(courseId, chapters)
        # once we have the chapter details, we can load all of the variation htmls
        if Pgn.doPgn == Pgn.PGN_INCREMENTAL:
            appendToFile = False
            for i in range(len(chapterResults)):
                bset, vset = chapterResults[i]
                # get each variation individually
                for vi in range(len(vset)):
                    thisVarDet = WebFetch.getVariationDetailFromTag(courseId, vset[vi], "Default")
                    thisVarDet.append(str(i + 1) + "." + str(vi + 1))
                    pgnOut = generateCoursePGNs(courseId, [thisVarDet])
                    Pgn.writeCoursePgnFile(courseId, pgnOut, appendToFile)
                    appendToFile = True
        elif Pgn.doPgn == Pgn.PGN_AFTER:
            variationResults = loadVariationInfo(courseId, chapterResults)
            # now all of the variation htmls are available locally
            pgnOut = generateCoursePGNs(courseId, variationResults)
            Pgn.writeCoursePgnFile(courseId, pgnOut, False)
        else:
            # still get the html even if we're not doing pgn...
            loadVariationInfo(courseId, chapterResults)

        print("----------")

    for variationId in variations:
        courseId = "one-off"
        print("--- Processing variation " + variationId + " fetch: " + WebFetch.flagNames[WebFetch.doFetch] + " pgn: " +
              Pgn.flagNames[Pgn.doPgn])
        thisVarResult = WebFetch.getVariationDetailFromId(courseId, variationId, "Default")
        if thisVarResult is None:
            continue
        thisVarResult.append("x.x")
        if Pgn.doPgn != Pgn.PGN_NONE:
            # in this case there's no distinction between incremental / after
            pgnOut = generateCoursePGNs(courseId, [thisVarResult])
            Pgn.writeVariationPgnFile(variationId, pgnOut)


def loadCourseInfo(courseId):
    print("--- getting course html for course " + courseId + " ---")
    courseBS, chapters = WebFetch.getCourseDetail(courseId, "Default")
    print("----- found course '" + WebFetch.getCourseName(courseBS) + "'")
    print("----- read " + str(len(chapters)) + " chapters")
    return courseBS, chapters


def loadChapterInfo(courseId, chapters):
    chapterResults = []

    chaptersRead = 0
    varsPreviewed = 0
    for c in chapters:
        thisResult = processChapter(courseId, str(c), "Default")
        varsPreviewed += len(thisResult[1])
        chapterResults.append(thisResult)
        chaptersRead += 1
        if chaptersRead > 500:
            break
    print(" - total of " + str(varsPreviewed) + " - variations previewed - ")
    return chapterResults


def loadVariationInfo(courseId, chapterResults):
    variationResults = []

    variationsRead = 0
    chapterNbr = 0  # used to build round string
    variationNbr = 0  # used to build round string
    for b, v in chapterResults:
        chapterNbr += 1
        variationNbr = 0
        for variation in v:
            variationNbr += 1
            thisVarDet = WebFetch.getVariationDetailFromTag(courseId, variation, "Default")
            if thisVarDet[0] is None:
                print(" - no HTML found for variation " + thisVarDet[1])
                continue
            roundStr = str(chapterNbr) + "." + str(variationNbr)
            thisVarDet.append(roundStr)
            variationResults.append(thisVarDet)
            variationsRead += 1
            if variationsRead > 5000:
                break
        if variationsRead > 5000:
            break
    print(" - total of " + str(variationsRead) + " - variations read - ")
    return variationResults


def generateCoursePGNs(courseId, variationResults):
    print(" Writing Course PGN file for course "+courseId)
    aggregatePgn = ""
    for [variation, variationId, roundStr] in variationResults:
        pgnOut = Pgn.createPgnFromHtml(courseId, variationId, variation, roundStr)
        if pgnOut is not None:
            aggregatePgn += pgnOut
    return aggregatePgn


def processChapter(courseId, tagStr, profileName):
    chapter = BeautifulSoup(tagStr, "html.parser")
    print("Parsing '" + WebFetch.getChapterName(chapter) + "' (" + profileName + ") ")
    chapterBS, variations = WebFetch.getChapterDetail(courseId, chapter, profileName)
    print(" returned  '" + WebFetch.getChapterName(chapter) + "' had (" + profileName + ") " + str(
        len(variations)) + " variations")
    return [chapterBS, variations]


if __name__ == "__main__":
    main()

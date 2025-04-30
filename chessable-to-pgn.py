import os
import shutil
import sys
from datetime import datetime
# import threading
# from multiprocessing import Pool

from bs4 import BeautifulSoup

import ConfigData
from WebFetch import WebFetch
from Pgn import Pgn

profileIds = []


def main():
    print("Chessable-to-PGN tool (c) 2025 John DeMastri under MIT License")
    if len(sys.argv) < 2:
        print("Please provide at least one courseID")
        return

    print("--- starting ---")
    print(datetime.now())
    processMode, courses, variations = processCommandLineParams()

    match processMode:
        case "interactive":
            quit = False
            while not quit:
                quit, courseIdAsList, variationIdAsList = getNextItemToProcess()
                if not quit:
                    processBatch(courseIdAsList, variationIdAsList, True, True, True)
                    print(" - PGN Generated")
            print("Exiting interactive mode!")
        case "webFetchThenPgn":
            processBatch(courses, variations, True, True, False)
        case "webFetch":
            processBatch(courses, variations, True, False, False)
        case "pgn":
            processBatch(courses, variations, False, True, False)
        case "webAndPgnByVar":
            for courseID in courses:
                processBatch([courseID], [], True, True, True)
            for variationId in variations:
                processBatch([], [variationId], True, True, True)
        case _:
            print("unknown process mode <" + processMode + ">")

    print("--- complete ---")
    print(datetime.now())


def getNextItemToProcess():
    choices = ["x", "c", "v"]
    s = ""
    while s not in choices:
        s = input("Please enter 'c' for course or 'v' for variation (and return), or 'x' to quit: ")
    if s == "x":
        return True, [], []
    if s == "c":
        c = input("Great, please enter the course ID: ")
        return False, [c], []
    if s == "v":
        v = input("Great, please enter the variation ID: ")
        return False, [], [v]

    return False, [], []


def processCommandLineParams():
    courses = []
    variations = []

    inCourse = False
    inChapter = False
    inVariation = False
    inMode = False
    inHtml = False
    inPgn = False
    processMode = "webAndPgnByVar"  # "webFetchThenPgn" # "webFetch" # "Pgn" # "webAndPgnByVar" #interactive
    for arg in sys.argv[1:]:
        if arg == 'c':
            inCourse = True
            inChapter = inVariation = False
            inMode = False
            inHtml = inPgn = False
        elif arg == 'ch':
            inChapter = True
            inCourse = inVariation = False
            inMode = False
            inHtml = inPgn = False
        elif arg == 'v':
            inVariation = True
            inCourse = inChapter = False
            inHtml = inPgn = False
            inMode = False
        elif arg == ('m'):
            inMode = True  # don't change where IDs go (course / chapter / var)
        elif arg == ('p'):
            inPgn = True  # don't change where IDs go (course / chapter / var)
        elif arg == ('h'):
            inHtml = True  # don't change where IDs go (course / chapter / var)
        elif inMode:
            processMode = arg
            inMode = False
            print("- setting process mode to <" + processMode + ">")
        elif inPgn:
            ConfigData.PGN_CACHE_PATH = arg
            inPgn = False
            print("- setting PGN root location to <" + arg + ">")
        elif inHtml:
            ConfigData.HTML_CACHE_PATH = arg
            inPgn = False
            print("- setting Html root location to <" + arg + ">")
        elif inCourse:
            courses.append(arg)
        elif inVariation:
            variations.append(arg)

    return processMode, courses, variations


def processBatch(courses, variations, doFetch, doPgn, doIncrementalPgn):
    WebFetch.doFetch = doFetch

    for courseId in courses:
        print("Processing of course " + courseId + " fetch: " + str(doFetch) + " pgn: " + str(doPgn))
        # print("--- getting variation html ---")
        courseBS, chapters = loadCourseInfo(courseId)
        # this first pass loads/saves all of the chapter htmls
        # running single-threaded - an hour trying to get threading and processing failed (selenium issues)
        chapterResults = loadChapterInfo(courseId, chapters)
        # once we have the chapter details, we can load all of the variation htmls
        if doPgn:
            if doIncrementalPgn:
                incremental = False
                for i in range(len(chapterResults)):
                    bset, vset = chapterResults[i]
                    # get each variation individually
                    for vi in range(len(vset)):
                        thisVarDet = WebFetch.getVariationDetailFromTag(courseId, vset[vi], "Default")
                        thisVarDet.append(str(i + 1) + "." + str(vi + 1))
                        pgnOut = generateCoursePGNs(courseId, [thisVarDet])
                        Pgn.writeCoursePgnFile(courseId, pgnOut, incremental)
                        # print(pgnOut)
                        incremental = True
            else:
                variationResults = loadVariationInfo(courseId, chapterResults)
                # now all of the variation htmls are available locally
                pgnOut = generateCoursePGNs(courseId, variationResults)
                # print(pgnOut)
                Pgn.writeCoursePgnFile(courseId, pgnOut, False)

    for variationId in variations:
        courseId = "one-off"
        print("Processing of variation " + variationId + " fetch: " + str(doFetch) + " pgn: " + str(doPgn))
        # print("--- getting variation html ---")
        thisVarResult = WebFetch.getVariationDetailFromId(courseId, variationId, "Default")
        if thisVarResult is None:
            continue
        thisVarResult.append("x.x")
        if doPgn:
            pgnOut = generateCoursePGNs(courseId, [thisVarResult])
            # prints...actually want to save this to disk somewhere...
            # print(pgnOut)
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
    chapterNbr = 0
    variationNbr = 0
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
    aggregatePgn = ""
    for [variation, variationId, roundStr] in variationResults:
        pgnOut = Pgn.createPgnFromHtml(courseId, variationId, variation, roundStr)
        aggregatePgn += pgnOut
    return aggregatePgn


def buildTestingProfiles(ref: str, prefix: str, pool_size: int):
    global profileIds
    for x in range(pool_size):
        srcDir = ConfigData.TESTING_PROFILE_BASE_DIR + "/" + "Default"
        destDir = ConfigData.TESTING_PROFILE_BASE_DIR + "/" + prefix + str(x)
        if not os.path.exists(destDir):
            shutil.copytree(srcDir, destDir, dirs_exist_ok=True)
        profileIds.append(prefix + str(x))


def destroyTestingProfiles(str, prefix: str, pool_size: int):
    for x in range(pool_size):
        thisDir = ConfigData.TESTING_PROFILE_BASE_DIR + "/" + prefix + str(x)
        shutil.rmtree(thisDir)


def processChapter(courseId, tagStr, profileName):
    # print("In pool fn '" + tagStr + "' ("+profileName+") ")
    chapter = BeautifulSoup(tagStr, "html.parser")
    print("Parsing '" + WebFetch.getChapterName(chapter) + "' (" + profileName + ") ")
    chapterBS, variations = WebFetch.getChapterDetail(courseId, chapter, profileName)
    print(" returned  '" + WebFetch.getChapterName(chapter) + "' had (" + profileName + ") " + str(
        len(variations)) + " variations")
    # print(" leaving pool fn '" + chessable-to-pgn.getChapterName(chapter) + "' had ("+profileName+") ")
    return [chapterBS, variations]


def processChapterFake(courseId, tagStr):
    chapter = BeautifulSoup(tagStr, "html.parser")
    print("----- reading chapter '" + WebFetch.getChapterName(chapter) + "'")


if __name__ == "__main__":
    main()

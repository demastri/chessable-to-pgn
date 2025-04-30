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
    print("Chessable-to-PGN tool (c) 2025 John DeMastri")
    if len(sys.argv) < 2:
        print("Please provide at least one courseID")
        return

    print("--- starting ---")
    print(datetime.now())
    processMode, webFetchMode, courses, variations = processCommandLineParams()

    match processMode:
        case "interactive":
            quit = False
            while not quit:
                quit, courseIdAsList, variationIdAsList, htmlOption, doPgn = getNextItemToProcess()
                # htmlOption: 1 = fetch new, 2 = fetch all, 3 = use existing (don't fetch)
                if not quit:
                    processBatch(courseIdAsList, variationIdAsList, htmlOption, doPgn, True)
                    print("--- HTML "+("New Items " if htmlOption==1 else ("All Items " if htmlOption==2 else "No Items "))+"Fetched")
                    print("--- PGN "+("" if doPgn else "Not ")+"Generated")
        case "webFetchThenPgn":
            processBatch(courses, variations, webFetchMode, True, False)
        case "webFetch":
            processBatch(courses, variations, webFetchMode, False, False)
        case "pgn":
            processBatch(courses, variations, WebFetch.FETCH_NONE, True, False)
        case "webAndPgnByVar":
            for courseID in courses:
                processBatch([courseID], [], webFetchMode, True, True)
            for variationId in variations:
                processBatch([], [variationId], webFetchMode, True, True)
        case _:
            print("unknown process mode <" + processMode + ">")

    print("--- complete ---")
    print(datetime.now())
    if processMode == "interactive":
        input("Exiting interactive mode!  Press ENTER to close this window.")


def getNextItemToProcess():
    srcChoices = ["q", "c", "v"]
    htmlChoices = ["f", "v", "x", "q"]
    pgnChoices = ["y", "n", "q"]
    htmlOptions = { "f":WebFetch.FETCH_NEW, "v":WebFetch.FETCH_ALL, "x":WebFetch.FETCH_NONE, "q":-1 }
    s = ""
    cOut = []
    vOut = []
    htmlOption = -1
    while s not in srcChoices:
        s = input("- Enter 'c' for course, 'v' for variation, 'q' to quit: ")
        if s == "":
            s = "c"
    if s == "q":
        return True, [], [], s, False
    if s == "c":
        c = input("-- Enter the course ID: ")
        cOut.append(c)
    if s == "v":
        v = input("-- Enter the variation ID: ")
        vOut.append(v)
    s = ""
    while s not in htmlChoices:
        s = input(
            "--- HTML - Fetch New HTML (f-default), oVerwrite All HTML (v), process eXisting HTML (x), or quit (q)? ")
        if s == "":
            s = "f"
    htmlOption = htmlOptions[s]
    while s not in pgnChoices:
        s = input("--- PGN - Write PGN (y-default / n / or q to quit)? ")
        if s == "":
            s = "y"

    return s == "q", cOut, vOut, htmlOption, s == "y"


def processCommandLineParams():
    courses = []
    variations = []

    inCourse = False
    inChapter = False
    inVariation = False
    inMode = False
    inFetchMode = False
    inHtml = False
    inPgn = False
    processMode = "webAndPgnByVar"  # "webFetchThenPgn" # "webFetch" # "Pgn" # "webAndPgnByVar" #interactive
    webFetchMode = WebFetch.FETCH_NEW
    for arg in sys.argv[1:]:
        if arg == 'c':
            inCourse = True
            inChapter = inVariation = False
            inFetchMode = inMode = False
            inHtml = inPgn = False
        elif arg == 'ch':
            inChapter = True
            inCourse = inVariation = False
            inFetchMode = inMode = False
            inHtml = inPgn = False
        elif arg == 'v':
            inVariation = True
            inCourse = inChapter = False
            inHtml = inPgn = False
            inFetchMode = inMode = False
        elif arg == ('m'):
            inMode = True  # don't change where IDs go (course / chapter / var)
        elif arg == ('w'):
            inFetchMode = True  # set how to process html files
        elif arg == ('p'):
            inPgn = True  # don't change where IDs go (course / chapter / var)
        elif arg == ('h'):
            inHtml = True  # don't change where IDs go (course / chapter / var)
        elif inFetchMode:
            webFetchMode = int(arg)
            inMode = False
            print("- setting web fetch mode to <" + str(webFetchMode) + "> - " + ("New Items " if webFetchMode==1 else ("All Items " if webFetchMode==2 else "No Items ")))
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

    return processMode, webFetchMode, courses, variations


def processBatch(courses, variations, doFetch, doPgn, doIncrementalPgn):
    WebFetch.doFetch = doFetch

    for courseId in courses:
        print("--- Processing course " + courseId + " fetch: " + ("New Items " if doFetch == 1 else ("All Items " if doFetch == 2 else "No Items ")) + "pgn: " + str(doPgn))
        # print("--- getting variation html ---")
        courseBS, chapters = loadCourseInfo(courseId)
        # this first pass loads/saves all of the chapter htmls
        # running single-threaded - an hour trying to get threading and processing failed (selenium issues)
        print("----------")

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
        else: # still get the html even if we're not doing pgn...
            loadVariationInfo(courseId, chapterResults)

        print("----------")

    for variationId in variations:
        courseId = "one-off"
        print("--- Processing variation " + variationId + " fetch: " + ("New Items " if doFetch == 1 else ("All Items " if doFetch == 2 else "No Items ")) + "pgn: " + str(doPgn))
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
        if pgnOut is not None:
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

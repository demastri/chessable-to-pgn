#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: chessable-tp-pgn.py
Author: John DeMastri
Create Date: 2025-04-27
Version: 0.3
Description: Entry point and main workflow driver for the application

License: MIT License
Contact: chess@demastri.com
"""
import multiprocessing
from datetime import datetime
from time import sleep

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

"""
design notes - proper multiprocessing
only need them for loading html
in c-t-p.py the nethod processBatch synchrohnously loads html and writes to disk, then writes pgn
breaking these apart to work asynchronously would require a method to start processes

before any work is done, we can set the processes up - n for web fetching and one for writing pgn
when a file is needed, we can add it to the working queue for that process
    can round robin the processes - just adding work to the queue
note that the work from the command line will just be courses or variations
    as work completes, it may cause chapter or variations jobs to be started
as variation jobs complete, we can write pgn by adding a job to the working queue for the pgn process

when the process starts, it checks its working queue, while it's empty, it sleeps and checks again
    if it's not empty, it reads the first entry, fetches the html (if it doesn't exist), it writes it to disk 
    then writes the id to its complete queue and removes it from its working queue. 
    
actually, could have course processes, chapter processes, and variation processes.
the fanout is like 1 course -> 15 chapters each -> 20 variations each...  
    so maybe 1 course process, 3 chapter processes, and 10 variation processes.
then when a variation loads, it would parse and add jobs to the variation, and variation / pgn, and pgn. 
when course loads, it would parse and add jobs to the chapter, and chapter/variation, and variation / pgn
Each one can kill the downstream processes when it's done.

This way the main process simply starts the jobs from the input parameters, everything is done downstream
The main process ends when all of the processes are idle.

"""
def worker(qIn, qOut, id):
    while True:
        item = qIn.get()
        if item is None:
            qIn.task_done()
            break
        print(f"Process {multiprocessing.current_process().name} processing: {item}")
        content = WebFetch.loadHtmlFromWeb("https://www.chessable.com/variation/5094106", profileName="Default") #"Profile "+str(id))
        print(f"Process {multiprocessing.current_process().name} Back from getting a web page")
        WebFetch.writeHtmlToFile(f"./html/{item}.html", content)
        print(f"Process {multiprocessing.current_process().name} web page written")
        qOut.put(item)
        qIn.task_done()
    print(f"Process {multiprocessing.current_process().name} exiting")

def generateQueues():
    working = multiprocessing.JoinableQueue()
    completed = multiprocessing.JoinableQueue()
    return working, completed

def startPool(poolSize, working, completed, worker):
    processes = []
    for i in range(poolSize):
        p = multiprocessing.Process(target=worker, args=(working,completed, i), name=f"Worker-{i}")
        processes.append(p)
        p.start()
    return processes


def testMultiProc(poolSize, workSize):

    # set up the queues and processes
    working, completed = generateQueues()
    processes = startPool(poolSize, working, completed, worker)

    print(f"Building Profiles")
    #WebFetch.buildTestingProfiles("Profile ", poolSize)

    # do some work on the processes
    for item in range(workSize):
        working.put(item)
    print(f"Data loaded into Queue")

    totalCount = 0
    while totalCount < workSize:
        totalCount += 1
        print(str(completed.get())+" was processed - item count: "+str(totalCount))
        completed.task_done()

    # at this point the queues are empty, processes are active, but still running
    # tell the processes to shut down when done
    print(f"Read inputs, processed outputs, sending kill signal")
    for item in range(poolSize):
        working.put(None)

    working.join()
    completed.join()
    print(f"Queues joined")

    for p in processes:
        p.join()
        print(f"Process {p.name} joined")

    print(f"Destroying Profiles")
    #WebFetch.destroyTestingProfiles("Profile ", poolSize)

    print(f"parent Process ending")

if __name__ == "__main__":
    testMultiProc(2, 4)
    #main()

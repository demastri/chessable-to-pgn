#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: Pgn.py
Author: John DeMastri
Create Date: 2025-04-27
Version: 0.3
Description: This script parses HTML and retrieves the information necessary to write as PGN files.
Given variation information as bs4 elements and walks it to find header, move and commentary information.

License: MIT License
Contact: chess@demastri.com
"""
import re
from pathlib import Path

import Utilities
from WebFetch import WebFetch
import ConfigData

PGN_COURSE_PATH = ConfigData.PGN_CACHE_PATH + 'course/'
PGN_VARIATION_PATH = ConfigData.PGN_CACHE_PATH + 'variation/'
PGN_WRITE_KEY_MOVE = True

STARTING_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # starting position

count = 0
firstMove = True
lastSeenFenParts = ""
lastSeenSan = ""
keyWritten = False


class Pgn:
    PGN_NONE = 0
    PGN_INCREMENTAL = 1
    PGN_AFTER = 2
    flagNames = ["none", "incremental", "after"]

    doPgn = PGN_INCREMENTAL

    def __init__(self):
        Pgn.doPgn = Pgn.PGN_INCREMENTAL

    @classmethod
    def createPgnFromHtml(cls, courseId: str, variationId, variation, roundStr):
        global count
        global firstMove
        global keyWritten
        count = 0
        firstMove = True
        keyWritten = False

        name, chapter, moves, term, inputFEN = WebFetch.getVariationParts(variation)

        if chapter == []:
            print(" - HTML not found for variation")
            return None
        if inputFEN != STARTING_POSITION:
            print("Variation does not begin at starting position")
        result = Pgn.getGameResult(term)
        outPgn = Pgn.buildHeader(courseId, variationId, name, chapter, result, roundStr, inputFEN)
        outPgn += Pgn.buildMoveBody(moves, 0)
        # there's are two odd chessbase bugs in PGN Import - see included "ChessBase import issue.pgn":
        #  found In CB17, v37 - May '25
        # 1 - if there's are trailing comment(s) in a game (nothing after it but the game terminator)
        #  and just before the comment(s) is a variation, not a move, THEN these trailing comment(s) will render
        #  at the BEGINNING of the game, and depending on if the game started from a FEN provided position or not,
        #  any initial comments (before move 1) get mangled as well.
        #  (This one I actually saw in the original .Net version of the tool, and thought it was in my PGN generator, HA!)
        # 2 - if the last thing in a comment set (incl in variations) after a move is a number, CB consumes it and
        #   usually displays as move time - the only exception would be for %clk or %emt tags, which will never be in
        #   Chessable variations.
        # The workarounds, which are only slightly nasty are as follows:
        # 1 - look at the last things written as pgn if it's variation, comment ... n x comment ... comment terminator,
        #   then insert a null move prior to the last comment so it renders more correctly
        #   (CB ignores whitespace anyway, might make processing easier to concatenate comments (s/} {//)
        # 2 - look at the last item in any comment set.  If it's a number, tack on something ("_") so CB ignores it
        outPgn = outPgn.replace( "}  {", "") # clear sequential comments, CB ignores the whitespace...
        outPgn, allOpens, allCloses = insertNullMoveBeforeLastComment(outPgn)
        outPgn = escapeLastNumberInComments(outPgn, allOpens, allCloses)
        outPgn += Pgn.buildGameResult(result)
        return re.sub(r' +', ' ', outPgn)

    @classmethod
    def buildHeader(cls, courseId, variationId, name: str, chapter, result, roundStr, FEN):
        # we have 6 pieces of info to be conveyed: course, chapter, variation title, variation url, location as round, and result
        # these can be mapped as:
        #  result => Result
        #  location => Round (4th var in 3rd chapter is 3.4)
        #  course title => Event
        #  variation URL => Site
        #  chapter name => White
        #  variation title => Black
        # Most viewers break the names into first and last based on the ',' character
        # We can prevent that by replacing any "," with '-' (can see if this looks ok...)
        courseTitle = re.sub(r'\s+', ' ', chapter[0].text.replace("\n", "")).strip()
        chapterTitle = re.sub(r'\s+', ' ', chapter[2].text.replace("\n", "")).strip().replace(",", "-")
        variationTitle = re.sub(r'\s+', ' ', name.replace("\n", "")).strip().replace(",", "-")
        variationUrl = ConfigData.BASE_CHESSABLE_URL + "variation/" + str(variationId)

        header = """[Event \"""" + courseTitle + """\"]
[Site \"""" + variationUrl + """/\"]
[Date \"????.??.??\"]
[Round \"""" + roundStr + """\"]
[White \"""" + chapterTitle + """\"]
[Black \"""" + variationTitle + """\"]
[Result \"""" + result + """\"]
"""
        if FEN != STARTING_POSITION:
            header += "[FEN \"" + FEN + "\"]\n"
        header += "\n"

        return header

    @classmethod
    def buildMoveBody(cls, moves, depth):
        global count
        global firstMove
        global lastSeenFenParts
        global lastSeenSan
        global keyWritten

        # Notes:
        #  c.text is actually recursive.  CommentInMove is not a PGN comment, contains both variations and comments!!
        #    when we know what we're working on, wrap variations in (), comments in {}
        #  ToDo: text has some formatting <h1>...that should be better represented in PGN comments (whether CB reads or not)
        outString = ""
        depth += 1
        count += 1
        # print(" " * depth + "x")
        outString = ""

        for c in moves:
            firstKey = False
            if c.name == "span" and c.get("class") is not None and "commentInVariation" in c["class"]:
                outString += " { " + c.text + " } "
            if c.name == "div" and c.get("class") is not None and (
                    "openingNum" in c["class"] and Pgn.isTerminator(c.text)):
                outString += "\n\n " + c.text + "\n\n"

            if c.name == "div" and c.get("class") is not None and (
                    "whiteMove" in c["class"] or "blackMove" in c["class"]):
                keyStr = ""
                if PGN_WRITE_KEY_MOVE and "is_key" in c["class"]:
                    if not keyWritten:
                        keyWritten = True
                        keyStr = " { -KEY- } "

                if firstMove or "whiteMove" in c["class"]:
                    outString += c["data-move"] + " "
                    firstMove = False

                outString += keyStr + c["data-san"] + " "
                lastSeenSan = c["data-san"]
                lastSeenFenParts = c["data-fen"].split()
            if c.name == "span" and c.get("class") is not None and "commentMoveSmall" in c["class"]:
                if c.get("data-san") is not None:
                    fenParts = c[
                        'data-fen'].split()  # "2r2rk1/3nbpp1/pp1p3P/4pP2/P1q2P2/2N1BQ2/1Pn3BP/3R1R1K b - - 0 22"
                    if not firstMove and isWhite == fenParts[1]:  # two successive moves with the same color
                        print(" ### repeated move?? ### " + c["data-san"])
                    isWhite = fenParts[1] == "b"  # after this move...
                    moveNbr = int(fenParts[5])  # if it's white to move before this fen, then the number is 1 high
                    if not isWhite:
                        moveNbr -= 1
                    moveNbr = str(moveNbr)
                    if firstMove and fenParts[1] != lastSeenFenParts[1]:
                        # this is likely enough of a check...  repeat the last move seen
                        # this is a first move in a variation. it should be able to replace the last move seen
                        # if it's the next move. we need to repeat the prior move
                        # this can be seen at the end of a game, when the author provides a potential or actual continuation
                        # so it's a ply behind where this move thinks it is...
                        # print( "Mismatch onMove in variation ..." )
                        # print( lastSeenFenParts, fenParts )
                        moveNbr = moveNbr if not isWhite else str(int(moveNbr) - 1)
                        isWhite = not isWhite
                        outString += moveNbr
                        if isWhite:
                            outString += ". "
                        else:
                            outString += "... "
                        outString += lastSeenSan + " "
                        # ok, now set up to handle this actual move
                        firstMove = False
                        isWhite = not isWhite

                    if firstMove or isWhite:
                        outString += moveNbr
                        if isWhite:
                            outString += ". "
                        else:
                            outString += "... "
                        firstMove = False
                    outString += c["data-san"]
                    if Pgn.getNag(c.text) != "":
                        outString += Pgn.getNag(c.text)  # nag could be included in display text
                    outString += " "
            if c.name == "span" and c.get("class") is not None and "annotation" in c["class"] and c.get(
                    "data-original-title") is not None and c["data-original-title"] != "" and Pgn.getNag(c.text) != "":
                outString = outString[:-1] + Pgn.getNag(c.text) + " "  # or nag could be defined in a separate span

            # for embedded variations, write "(" then kids pgn, then ")"
            if c.name == "span" and c.get("class") is not None and (
                    "commentTopvar" in c["class"] or "commentSubvar" in c["class"]):
                outString += " ( "
                firstMove = True

            # in any event, make sure we write any kid nodes' data
            kids = c.findChildren(recursive=False)
            outString = outString + Pgn.buildMoveBody(kids, depth)

            if c.name == "span" and c.get("class") is not None and (
                    "commentTopvar" in c["class"] or "commentSubvar" in c["class"]):
                outString += " ) \n"

        # print(" " * depth + "/x")

        depth -= 1

        return outString

    @classmethod
    def getNag(cls, c):
        nagStrings = {"!": 1, "?": 2, "!!": 3, "??": 4, "!?": 5, "?!": 6,
                      "=": 11, "∞": 13,
                      "⩲": 14, "⩱": 15, "±": 16, "∓": 17, "+-": 18, "-+": 19}

        if (len(c) >= 2 and c[len(c) - 2:] in nagStrings.keys()):
            return " $" + str(nagStrings[c[len(c) - 2:]])
        if (len(c) >= 1 and c[len(c) - 1:] in nagStrings.keys()):
            return " $" + str(nagStrings[c[len(c) - 1:]])
        # note, this can occur in the next child after the move text:  <span class="annotation" data-original-title="Good move">!</span>
        return ""

    @classmethod
    def isTerminator(cls, s):
        if s is None:
            return ""
        termStrings = ["*", "1-0", "0-1", "1/2-1/2"]
        return s.strip() in termStrings

    @classmethod
    def writeCoursePgnFile(cls, courseId, pgnOut, incremental):
        mode = "a" if incremental else "w"
        path = Path(PGN_COURSE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        with open(PGN_COURSE_PATH + courseId + ".pgn", mode, encoding='utf-8') as file:
            return file.write(pgnOut)

    @classmethod
    def writeVariationPgnFile(cls, variationId, pgnOut):
        path = Path(PGN_VARIATION_PATH)
        path.mkdir(parents=True, exist_ok=True)
        with open(PGN_VARIATION_PATH + variationId + ".pgn", "w", encoding='utf-8') as file:
            return file.write(pgnOut)

    @classmethod
    def buildGameResult(cls, result):
        return "\n " + result + " \n\n"

    @classmethod
    def getGameResult(cls, result):
        for x in result:
            if Pgn.isTerminator(x.text):
                return x.text
        return "*"


def insertNullMoveBeforeLastComment(pgn):
    # the specific case I'm looking for is if, at the root level, the last things in the file are variation, then comment
    # if so, insert a null move just before the last comment
    iComment, allOpens, allCloses = findLastRootComment(pgn)
    lastMove, lastVariation, lastComment = findLastMove(pgn)
    if lastMove < lastVariation < lastComment:
        print(" - found a game with move - variation - comment ending")
        return pgn[:iComment] + " Z0 " + pgn[iComment:], allOpens, allCloses
    return pgn, allOpens, allCloses


def escapeLastNumberInComments(pgn, opens, closes):
    curStart = 0
    outPgn = ""
    curOpen = []
    for thisClose in closes:
        while len(opens) > 0 and (len(curOpen) == 0 or opens[0] < thisClose):
            curOpen.append(opens[0])
            opens = opens[1:]
        thisOpen = curOpen.pop()
        # here thisopen, thisClose are the current nested comment we're dealing with.
        # if the next open is only 3 away "}  {", we don't have to worry about this pair
        if len(pgn) > thisClose+3 and pgn[thisClose+3] == "{":
            continue
        # ok - not followed by another comment, let's see if the last elt in this set is a number
        parts = pgn[thisOpen:thisClose].split()
        if len(parts) > 0 and Utilities.is_integer(parts[len(parts) - 1]):
            # we have to escape this.
            print(" Found a comment set ending in a number")
            outPgn = outPgn + pgn[curStart:thisClose+1] + " { _ } "
            curStart = thisClose+1
    outPgn = outPgn + pgn[curStart:]

    return outPgn


def findLastRootComment(pgn):
    opens = []
    closes = []
    depth = 1
    curLast = -1
    for i in range(len(pgn)):
        ch = pgn[i]
        if ch == "(":
            depth += 1
        if ch == ")":
            depth -= 1
        if ch == "{":
            opens.append(i)
            if depth == 1:
                curLast = i
        if ch == "}":
            closes.append(i)
    return curLast, opens, closes


def findLastRootVariation(pgn):
    depth = 1
    curLast = -1
    for i in range(len(pgn)):
        ch = pgn[i]
        if ch == "(":
            if depth == 1:
                curLast = i
            depth += 1
        if ch == ")":
            depth -= 1
    return curLast


def findLastMove(pgn):
    lastMove = -1
    lastVariation = -1
    lastComment = -1

    inComment = False
    inVariation = False
    inTag = False

    depth = 1
    parts = pgn.split()
    for i in range(len(parts)):
        part = parts[i]

        if depth == 1 and part == "{":
            inComment = True
            lastComment = i
        elif depth == 1 and part == "}":
            inComment = False
        elif part == "(":
            if depth == 1:
                inVariation = True
                lastVariation = i
            depth += 1
        elif part == ")":
            depth -= 1
            if depth == 1:
                inVariation = False
        elif part.find("[") == 0 and not inTag:
            inTag = True
        elif part.find("]") == len(part) - 1 and inTag:
            inTag = False
        elif depth == 1 and not inComment and not inVariation and not inTag:  # possible move
            if part[len(part) - 1:] == ".":  # move number
                continue
            if part.find("$") == 0:  # diacritic
                continue
            if part == "Z0":  # null move
                continue
            lastMove = i  # what else could it be...

    return lastMove, lastVariation, lastComment

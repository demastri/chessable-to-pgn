import re
from pathlib import Path

from WebFetch import WebFetch
import ConfigData

PGN_COURSE_PATH = ConfigData.PGN_CACHE_PATH + 'course/'
PGN_VARIATION_PATH = ConfigData.PGN_CACHE_PATH + 'variation/'

count = 0
firstMove = True

class Pgn:
    @classmethod
    def createPgnFromHtml(cls, courseId:str, variationId, variation, roundStr):
        count=0
        firstMove = True
        name, chapter, moves, term = WebFetch.getVariationParts(variation)
        result = Pgn.getGameResult(term)
        outPgn = Pgn.buildHeader(courseId, variationId, name, chapter, result, roundStr)
        outPgn += Pgn.buildMoveBody(moves, 0)
        outPgn += Pgn.buildGameResult(result)
        # print(str(count))
        return re.sub(r' +', ' ', outPgn)

    @classmethod
    def buildHeader(cls, courseId, variationId, name:str, chapter, result, roundStr):
        courseTitle = re.sub(r'\s+', ' ', chapter[0].text.replace( "\n", ""))
        courseChapter = chapter[2].text
        header = """[Event \""""+courseTitle.strip()+" - " + courseChapter.strip() + """\"]
[Site \"chessable.com/variation/"""+str(variationId)+"""/\"]
[Date \"????.??.??\"]
[Round \""""+roundStr+"""\"]
[White \"\"]
[Black \"\"]
[Result \""""+result+"""\"]
[Title \""""+name.strip()+"\"]\n"
        return header


    @classmethod
    def buildMoveBody(cls, moves, depth):
        global count
        global firstMove
        # this is actually much closer to correct than it has a right to be
        # two obvious things to work on:
        #  c.text is actually recursive.  CommentInMove is not a PGN comment, contains both variations and comments!!
        #    so will have to  back out the {}, and when we know which, wrap variations in (), comments in {}
        #  text has some formatting <h1>...that should be better represented in PGN comments (whether CB reads or not)
        outString = ""
        depth += 1
        count += 1
        #print(" " * depth + "x")
        outString = ""

        for c in moves:
            if c.name == "span" and c.get("class") is not None and "commentInVariation" in c["class"]:
                outString += "{ "+c.text+" } "
            if c.name == "div" and c.get("class") is not None and ("openingNum" in c["class"] and Pgn.isTerminator(c.text)):
                outString += "\n\n "+c.text+"\n\n"

            if c.name == "div" and c.get("class") is not None and ("whiteMove" in c["class"] or "blackMove" in c["class"]):
                if firstMove or "whiteMove" in c["class"]:
                    outString += c["data-move"] + " "
                    firstMove = False
                outString += c["data-san"]+" "
            if c.name == "span" and c.get("class") is not None and "commentMoveSmall" in c["class"]:
                if c.get("data-san") is not None:
                    fenParts = c['data-fen'].split()    # "2r2rk1/3nbpp1/pp1p3P/4pP2/P1q2P2/2N1BQ2/1Pn3BP/3R1R1K b - - 0 22"
                    isWhite = fenParts[1] == "b"    # after this move...
                    moveNbr = int(fenParts[5]) # if it's white to move before this fen, then the number is 1 high
                    if not isWhite:
                        moveNbr -= 1
                    moveNbr = str(moveNbr)
                    if firstMove or isWhite:
                        outString += moveNbr
                        if isWhite:
                            outString += ". "
                        else:
                            outString += "... "
                        firstMove = False
                    outString += c["data-san"]
                    if Pgn.getNag(c.text) != "":
                        outString += Pgn.getNag(c.text) # nag could be included in display text
                    outString += " "
            if c.name == "span" and c.get("class") is not None and "annotation" in c["class"] and c["data-original-title"] != "" and Pgn.getNag(c.text) != "":
                outString = outString[:-1] + Pgn.getNag(c.text) + " " # or nag could be defined in a separate span

            #for embedded variations, write "(" then kids pgn, then ")"
            if c.name == "span" and c.get("class") is not None and ("commentTopvar" in c["class"] or "commentSubvar" in c["class"]):
                outString += "( "
                firstMove = True

            # in any event, make sure we write any kid nodes' data
            kids = c.findChildren(recursive=False)
            outString = outString + Pgn.buildMoveBody(kids, depth)

            if c.name == "span" and c.get("class") is not None and ("commentTopvar" in c["class"] or "commentSubvar" in c["class"]):
                outString += " ) \n"


        #print(" " * depth + "/x")

        depth -= 1

        return outString

    @classmethod
    def getNag(cls, c):
        nagStrings = { "!": 1, "?": 2, "!!": 3, "??": 4, "!?": 5, "?!": 6,
                       "=": 11, "∞": 13,
                       "⩲": 14, "⩱": 15, "±": 16, "∓": 17, "+-": 18, "-+": 19 }
        # at the very least, I need example characters for 15 and 17 - black slightly and moderate adv

        if(len(c)>=2 and c[len(c)-2:] in nagStrings.keys()):
            return " $"+str(nagStrings[c[len(c)-2:]])
        if(len(c)>=1 and c[len(c)-1:] in nagStrings.keys()):
            return " $"+str(nagStrings[c[len(c)-1:]])

        # note, this occurs in the next child after the move text:  <span class="annotation" data-original-title="Good move">!</span>

        return ""

    @classmethod
    def isTerminator(cls, s):
        if s is None:
            return ""
        termStrings = ["*", "1-0", "0-1", "1/2-1/2"]
        return s.strip() in termStrings

    @classmethod
    def writeCoursePgnFile( cls, courseId, pgnOut, incremental ):
        mode = "a"  if incremental else "w"
        path = Path(PGN_COURSE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        with open(PGN_COURSE_PATH+courseId+".pgn", mode, encoding='utf-8') as file:
            return file.write(pgnOut)

    @classmethod
    def writeVariationPgnFile( cls, variationId, pgnOut ):
        path = Path(PGN_VARIATION_PATH)
        path.mkdir(parents=True, exist_ok=True)
        with open(PGN_VARIATION_PATH+variationId+".pgn", "w", encoding='utf-8') as file:
            return file.write(pgnOut)

    @classmethod
    def buildGameResult(cls, result):
        return "\n "+result+" \n\n"

    @classmethod
    def getGameResult( cls, result ):
        for x in result:
            if Pgn.isTerminator(x.text):
                return x.text
        return "*"

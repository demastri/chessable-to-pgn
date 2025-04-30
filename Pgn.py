import re
from pathlib import Path

from WebFetch import WebFetch
import ConfigData

PGN_COURSE_PATH = ConfigData.PGN_CACHE_PATH + 'course/'
PGN_VARIATION_PATH = ConfigData.PGN_CACHE_PATH + 'variation/'

count = 0
firstMove = True
lastSeenFenParts = ""
lastSeenSan = ""

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
        courseTitle = re.sub(r'\s+', ' ', chapter[0].text.replace( "\n", "")).strip()
        chapterTitle = re.sub(r'\s+', ' ', chapter[2].text.replace( "\n", "")).strip().replace(",","-")
        variationTitle = re.sub(r'\s+', ' ', name.replace( "\n", "")).strip().replace(",","-")
        variationUrl = ConfigData.BASE_CHESSABLE_URL+"variation/"+str(variationId)

        header = """[Event \""""+courseTitle+ """\"]
[Site \""""+variationUrl+"""/\"]
[Date \"????.??.??\"]
[Round \""""+roundStr+"""\"]
[White \""""+chapterTitle+"""\"]
[Black \""""+variationTitle+"""\"]
[Result \""""+result+"\"]\n"
        return header


    @classmethod
    def buildMoveBody(cls, moves, depth):
        global count
        global firstMove
        global lastSeenFenParts
        global lastSeenSan
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
                lastSeenSan = c["data-san"]
                lastSeenFenParts = c["data-fen"].split()
            if c.name == "span" and c.get("class") is not None and "commentMoveSmall" in c["class"]:
                if c.get("data-san") is not None:
                    fenParts = c['data-fen'].split()    # "2r2rk1/3nbpp1/pp1p3P/4pP2/P1q2P2/2N1BQ2/1Pn3BP/3R1R1K b - - 0 22"
                    if not firstMove and isWhite == fenParts[1]: # two successive moves with the same color
                        print( " ### repeated move?? ### " + c["data-san"] )
                    isWhite = fenParts[1] == "b"    # after this move...
                    moveNbr = int(fenParts[5]) # if it's white to move before this fen, then the number is 1 high
                    if not isWhite:
                        moveNbr -= 1
                    moveNbr = str(moveNbr)
                    if firstMove and fenParts[1] != lastSeenFenParts[1]: # this is likely enough of a check...  repeat the last move seen
                        # this is a first move in a variation. it should be able to replace the last move seen
                        # if it's the next move. we need to repeat the prior move
                        # this can be seen at the end of a game, when the author provides a potential or actual continuation
                        # so it's a ply behind where this move thinks it is...
                        # print( "Mismatch onMove in variation ..." )
                        # print( lastSeenFenParts, fenParts )
                        moveNbr = moveNbr if not isWhite else str(int(moveNbr)-1)
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
                        outString += Pgn.getNag(c.text) # nag could be included in display text
                    outString += " "
            if c.name == "span" and c.get("class") is not None and "annotation" in c["class"] and c.get("data-original-title") is not None and c["data-original-title"] != "" and Pgn.getNag(c.text) != "":
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

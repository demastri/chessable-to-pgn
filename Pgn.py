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
        name, chapter, moves = WebFetch.getVariationParts(variation)
        result = Pgn.getGameResult(moves)
        outPgn = Pgn.buildHeader(courseId, variationId, name, chapter, result, roundStr)
        outPgn += Pgn.buildMoveBody(moves, 0)
        outPgn += Pgn.buildGameResult(result)
        # print(str(count))
        return outPgn

    @classmethod
    def buildHeader(cls, courseId, variationId, name:str, chapter, result, roundStr):
        courseTitle = chapter[0].text
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
            if c.name == "div" and c.get("class") is not None and ("whiteMove" in c["class"] or "blackMove" in c["class"]):
                if firstMove or "whiteMove" in c["class"]:
                    outString += c["data-move"] + " "
                    firstMove = False
                outString += c["data-san"]+" "
            if c.name == "span" and c.get("class") is not None and "commentMoveSmall" in c["class"]:
                if c.get("data-san") is not None:
                    fenParts = c['data-fen'].split()    # "2r2rk1/3nbpp1/pp1p3P/4pP2/P1q2P2/2N1BQ2/1Pn3BP/3R1R1K b - - 0 22"
                    isWhite = fenParts[1] == "b"    # after this move...
                    moveNbr = fenParts[5]
                    if firstMove or isWhite:
                        outString += moveNbr
                        if isWhite:
                            outString += ". "
                        else:
                            outString += "... "
                        firstMove = False
                    outString += c["data-san"]+" "
            if c.name == "span" and c.get("class") is not None and "commentTopvar" in c["class"]:
                outString += "( "
                firstMove = True


            kids = c.findChildren(recursive=False)
            outString = outString + Pgn.buildMoveBody(kids, depth)

            if c.name == "span" and c.get("class") is not None and "commentTopvar" in c["class"]:
                outString += " ) \n"


        #print(" " * depth + "/x")

        depth -= 1

        return outString

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
        return "*"

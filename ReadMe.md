Chessable to PGN Tooling
-
- Release Notes
- Installation
- First time Setup
- Usage
- PGN Tags Generated
- Testing and obvious notes

Release Notes
-
- v0.10 - 27-Apr-2025 - absolutely a pre-release version
  - Set the tool up its own standalone repo
  - Does a good job of fetching html, and generates passable PGN for simple game files
  - Known issues
    - Does not handle complex, nested variations well
    - There are cases where the author says something like this in a comment:
      - "now we try 13. g4 which attempts to bust open the K-side like this: 13. g4 Nf3 ..."
      - the repeated g4 move is in the same variation comment in the html twice, which would translate to an illegal move
      - I've seen this several times - will release a fix when it's available
    - Does not yet properly handle game terminators/results correctly
    - No support for diacritic or evaluation glyphs.  These were handled in the (old) .net version, and will be eventually ported to this version as well.
    - Multiprocessing does not work.  Skeletal code to create/destroy profiles exists, but these should not be required.  Work will continue.  This one fix will significantly cut overall translation time significantly. 
    - May add support for chapter batches in addition to variations and courses.  Might be more manageable.  Or just fix multiprocessing... 

Installation
-
This tool uses several helpers to perform it's job:

- A reasonably recent Python install - tested on 3.13.3 - have done no testing on other versions
- Chrome for Testing (which requires node to install the current stable version)
  - if you don't have node/npm installed, go here: https://nodejs.org/en/download
  - To get the lastest stable version of Chrome for Testing, run this at a prompt that can see npm:
    - npx @puppeteer/browsers install chrome@stable
    - take note of the install location and version (see setup)
- Selenium
- Beautiful Soup
  - These two can just be installed as a regular Python package
  - (recommend as always using a bespoke conda or venv environment for all projects)

First time Setup
-
- In "configdata.py" set the following variables:
    - CHROME_FOR_TESTING_BINARY_LOC
      - the location of the binary you just installed, should look something like:
      - "C:/Users/john/chrome/win64-135.0.7049.114/chrome-win64/chrome.exe"
    - TESTING_PROFILE_BASE_DIR
      - The location that binary will look for profile data, should look something like:
      - "C:/Users/john/AppData/Local/Google/Chrome for Testing/User Data"
    - TESTING_PROFILE - the profile this browser should use - likely can leave as "Default"
    - HTML_CACHE_PATH - the place that read html files will be stored - default is './html/'
      - ./html/course
        - this is where course page html files are stored by course ID, like 24575.html
      - ./html/course/<courseID>  
        - this folder holds the retrieved html that course's chapter pages - 1/chapter
      - ./html/course/<courseID>/variation  
        - this folder holds all of the variation html files are stored 1/variation
      - /.html/course/one-off/variation  
        - this folder holds variation htmls loaded/processed directly (see usage)
    - PGN_CACHE_PATH - the place that generated pgn files will be stored - default is './pgn/'
      - ./pgn/course     
        - this folder holds files - one per course - containing all variations as pgn, like 24575.pgn
      - ./pgn/variation  
        - this folder holds files - one per variation - containing that id's variation as pgn, like 38877075.pgn
- Chrome for Testing Setup
  - you will want to take the executable for Chrome for Testing (the one in CHROME_FOR_TESTING_BINARY_LOC) and 
run it directly.  A browser window will open.  Set up a profile for testing (can be any ID you want - the point is
not to use your personal profile...)
  - While in this profile, log into chessable using your credential.  This is how selenium will access chessable.  Once you
have done this and can see your courses, etc., you can shut the browser down.

Usage
- 
- This is a command line tool that can be run at a prompt or from within an IDE
  - the main method is "python main.py m <mode> c <courseIDs> v <variationIDs>"
- CourseIDs and variationIDs are simply lists of the integer IDs Chessable has assigned to these items
  - to load an entire course, just specify the course ID, the tool will find all of the variations.
  - loading a single variation can be good for testing, or if you want to clear your commentary and start fresh with a variation.
- there are four modes that you can run the tool in:
  - webFetchThenPgn
    - this is the default mode.  the tool will pull all of the html for the specified courses and/or variations, 
then generate all of the pgn when that's done
    - note 1 - this can take a while, since chessable dynamically loads the html, we have to wait several seconds 
                for each page to finish loading
    - note 2 - this is interruptable - if you get 300 of 1000 variations fetched and restart the process, it will
              start at 301 (using whatever's already in the /course and /course/variations folders, and loading the 
              rest from the web)
    - note 3 - you can have courses and variations on the same command line, anything after a c is a courseID, anything
    after a v is a variationID  
    - ex1, for a course: "python main.py m webFetchThenPgn c 24575" loads and translates "The Art of Attack", resulting
            in a generated "/pgn/course/24575.pgn" file.  The loaded html files will be in the folders /course,
            /course/<courseID> and /course/<courseID>/variation folders
    - ex2, for a variation: "python main.py m webFetchThenPgn v 38877075" loads and translates the first variation
        in the first chapter of the "Checkmate Patterns" course, resulting in a generated "/pgn/variation/38877075.pgn"
        file, and the html will be in "/course/one-off/variation/38877075.html"
  - webFetch
    - this is just like webFetchThenPgn, except that it doesn't generate the pgn, just the cached html documents 
    in /html /html/course and /html/course/variation folders 
  - pgn
    - this is just like webFetchThenPgn, except that it doesn't fetch html, just generates pgn from any html that
    has been previously fetched
  - webAndPgnByVar
    - this is similar to webFetchThenPgn, but instead of loading all of the html, it generates pgn's as it processes 
    individual variations
    - so, normally, the tool fetches the course file, then all of the chapter files for the course, then all of the 
    variations in all of the chapters.  Only then does it go back and process the pgns for the fethced variations.
    - in this mode, it still fetches the course file and all of the chapter files for that course, but then for each 
    variation it fetches the html, then generates that html's pgn
      - note that the overall time to completion is about the same, but you get the first pgn MUCH faster this way, 
      if that matters.  
  - In testing, we typically let the tool fetch large course over a couple of hours, then run pgn on
  those fetched htmls.  The modes allow you to decide how best to process your courses.
  - We've also tried to run this in multiprocess mode, but consistently get selenium errors with multiple processes 
  simultaneously accessing the same profile, which should be impossible since we establish one profile per variation.  
  Anyone wanting to help resolve this should reach out, or generate a pull request. 

PGN Tags Generated
-
- A typical PGN has a Seven Tag Roster associated with it.  Not all of these make sense in this context.  
- It generates the following 8 tags (STR + Title).  Example and explanation: 
  - [Event "The Checkmate Patterns Manual - 1. Introduction"]  -- this tag has the course and chapter names for this variation
  - [Site "chessable.com/variation/38877075/"]  -- this tag has the url that points to this specific variation
  - [Date "????.??.??"] -- undefined, but the tag is required by many readers so this is provided as shown
  - [Round "x.x"]       -- This shows the chapter and variation in that chapter.  ex 4th var in the 3rd chapter would 
  be "3.4".  These are ORDINAL numbers based on their positions in the course, and do not correspond to any goofy
  chapter or variation numbering scheme used by the author
  - [White ""]          -- undefined, but the tag is required by many readers so this is provided as shown
  - [Black ""]          -- undefined, but the tag is required by many readers so this is provided as shown
  - [Result "*"]        -- undefined, but the tag is required by many readers so this is provided as shown (will eventually be corrected)
  - [Title "Next steps after mastering this course"] -- this is the title shown for this specific variation.

Testing and obvious notes
-
- To test this, I would start with one variation from a small course so that you can establish that the tool is setup 
correctly.  I've tried to explain how to do that, but there's no support, warranty or other channel to help you if you
have trouble, except maybe Reddit.  Good luck.
- This tool is intended to access only the courses YOU have access to so that you can better utilize content you already 
own (think: use a version of your 1 e4 rep course in SCID or Chessbase).  This is why YOU have to set up the browser with your
chessable credentials.  Good luck with better leveraging of your rep in correspondence games, etc...
- It is NOT intended to help share content you don't already own. If you're sharing chessable credentials, or
sharing the output of the tool with people that don't have access, you're violating chessable's terms of service, and just
making the world a worse place, overall.  You're why we can't have nice things.  Kill yourself.
- It is a consequence of modern development that this file is larger (in overall size) than any of the code files in the repo...


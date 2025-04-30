Chessable to PGN Tooling
-
- Installation
- First Time Setup
- Usage
- PGN Tags Generated
- Performance and Operational Notes
- Release Notes
- Open Items
- Testing and obvious notes

Installation
-
This tool uses several helpers to perform its job:

- A reasonably recent Python install - tested on 3.13.3 - have done no testing on other versions
- External dependencies
  - Chrome for Testing (which requires node to install the current stable version)
    - if you don't have node/npm installed, go here: https://nodejs.org/en/download
    - To get the lastest stable version of Chrome for Testing, run this at a prompt that can see npm:
      - npx @puppeteer/browsers install chrome@stable
      - take note of the install location and version (see setup)
- Python packages
  - These can just be installed as a regular Python packages (use your favorite package manager)
  - We recommend (as always) using a bespoke conda or venv environment for all Python projects
    - selenium
    - selenium-manager
    - beautifulsoup4
  
First Time Setup
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
      - `./html/course`
        - this is where course page html files are stored by course ID, like 24575.html
      - `./html/course/<courseID>`  
        - this folder holds the retrieved html that course's chapter pages - 1/chapter
      - `./html/course/<courseID>/variation`  
        - this folder holds all of the variation html files are stored 1/variation
      - `/.html/course/one-off/variation`  
        - this folder holds variation htmls loaded/processed directly (see usage)
    - PGN_CACHE_PATH - the place that generated pgn files will be stored - default is './pgn/'
      - `./pgn/course`     
        - this folder holds files - one per course - containing all variations as pgn, like 24575.pgn
      - `./pgn/variation`  
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
  - the entry point is main.py, and your command line will look something like:
    - `python main.py m <mode> c <courseIDs> v <variationIDs>`
- CourseIDs and variationIDs are simply lists of the integer IDs Chessable has assigned to these items
  - to load an entire course, just specify the course ID, the tool will find all of the variations.
    - to get a specific course ID, go to the course's home/info page.  The url is something like this example for
    Vukovic's excellent book:
      - https://www.chessable.com/the-art-of-attack-in-chess/course/24575/
      - The course ID in this case is just 24575
      - Very similar for variations, except the url is something like: https://www.chessable.com/variation/3968464/ 
      where the variation ID is (you guessed it) 3968464
  - loading a single variation can be good for testing, or if you want to clear your commentary and start fresh with a variation.
- there are five modes that you can run the tool in:
  - `interactive`
    - This is the most basic possible interactive prompt - enter the course or variation ID(s) you want to process, 
    one at a time, when prompted and it will process them.  This mode is helpful if you want to run the tool from a shortcut.
      - This is usually the only thing on the command line: `python main.py m interactive`
  - `webFetchThenPgn`
    - was originally the default mode, now the default is `webAndPgnByVar`, see below.
    - the tool will pull all htmls for the specified courses and/or variations, 
then generate all pgns when that's done
    - note 1 - this can take a while, since chessable dynamically loads the html, we have to wait several seconds 
                for each page to finish loading
    - note 2 - this is interruptable - if you get 300 of 1000 variations fetched and restart the process, it will
              start at 301 (using whatever's already in the /course and /course/variations folders, and loading the 
              rest from the web)
    - note 3 - you can have courses and variations on the same command line, anything after a c is a courseID, anything
    after a v is a variationID  
    - ex1, for a course: `python main.py m webFetchThenPgn c 24575` loads and translates "The Art of Attack", resulting
            in a generated `/pgn/course/24575.pgn` file.  The loaded html files will be in the folders `/course`,
            `/course/<courseID>` and `/course/<courseID>/variation` folders
    - ex2, for a variation: `python main.py m webFetchThenPgn v 38877075` loads and translates the first variation
        in the first chapter of the "Checkmate Patterns" course, resulting in a generated `/pgn/variation/38877075.pgn`
        file, and the html will be in `/course/one-off/variation/38877075.html`
  - `webFetch`
    - this is just like `webFetchThenPgn`, except that it doesn't generate the pgn, just the cached html documents 
    in `/html` `/html/course` and `/html/course/variation` folders 
  - `pgn`
    - this is just like webFetchThenPgn, except that it doesn't fetch html, just generates pgn from any html that
    has been previously fetched
  - `webAndPgnByVar`
    - this is the default mode.  
    - this is similar to `webFetchThenPgn`, but instead of loading all of the html, it inc`rementally generates pgn's as it processes 
    individual variations
    - so, in `webFetchThenPgn` mode, the tool fetches the course file, then all chapter files for the course, then all  
    variation files.  Only then does it go back and process the pgns for the fethced variations.
    - in this mode - `webAndPgnByVar`, it still fetches the course file and all of the chapter files for that course, 
    but then as it fetches the html for each variation, it also incrementally then generates that variation's pgn as 
    well (and adds it to the course pgn, if it's working on a course) 
      - note that the overall time to completion is about the same, but you get the first pgn MUCH faster this way, 
      if that matters.  
  - In testing, we typically let the tool fetch several large course over a couple of hours, then run pgn on
  those fetched htmls.  This way, we can test different pgn generation code without having to reload from the web each time.  
  The four different modes allow you to decide how best to process your courses.
  - We've also tried to run this in multiprocess mode, but consistently get selenium errors with multiple processes 
  simultaneously accessing the same profile, which should be impossible since we establish one profile per variation.  
  Anyone wanting to help resolve this should reach out, or do the work :) and generate a pull request. 

PGN Tags Generated
-
- A typical PGN has a Seven Tag Roster (STR) associated with it.  Not all of these make sense in this context, and we have 
extra info to share, so these tags have been co-opted...  Example STR and explanation: 
  - `[Event "The Checkmate Patterns Manual"]`  -- this tag has the course name that this variation belongs to
  - `[Site "chessable.com/variation/38877075/"]`  -- this tag has the url that points to this specific variation
  - `[Date "????.??.??"]` -- undefined, but the tag is required by many readers so this is provided as shown
  - `[Round "x.x"]`       -- This shows the chapter and variation in that chapter.  ex 4th var in the 3rd chapter would 
  be "3.4".  These are ORDINAL numbers based on their positions as listed in the course, and do not correspond to any goofy
  chapter or variation numbering scheme used by the author
  - `[White "1. Introduction"]`          -- this tag has the chapter name for this variation
  - `[Black "Next steps after mastering this course"]`          -- this tag has this variation's title
  - `[Result "*"]`        -- accurate if variation supplies it. Most don't - "*" is used in that case.
- Note that for player names (`"White"` and `"Black"` tags), most readers split the strings into first/last name depending 
on location of the first "," character.  To avoid this, all "," characters in actual chapter or variation name text are 
replaced with "-".
- This leads to PGN collections that look like this in ChessBase, with the course name to the right in the "Tournament" column, 
Chapters down the left side,variations just to their right, all in lexical order.  The Round column
reflects this order as well (as in the tag description above): 
  - ![img.png](img.png)

Performance and Operational Notes
-
- This tool is as fast as it can be, given that it's pulling dynamically assembled HTML from a server that isn't always that responsive.
- It can take 12-15 sec to get the final HTML and parse it into something usable
- This means that if you have a course with 150 variations across 7 chapters:
  - it's 158 HTML pulls (1 for the course, 1 for each chapter, 1 for each variation)
  - that's a nominal range of 158 * 12-15 sec, or 31.6 to 39.5 min.  
  - It's still much faster than you typing it in yourself.
    - That's a joke. They used to say that the C-1541 disk drive was only a little faster than you typing the code yourself into a C-64...and not quite as reliable.  I know...it's really just too funny to include on a page noone will ever see....
  - it does a good job of:
    - running unattended, so as long as your computer doesn't sleep, you can let really long runs (several courses??) run overnight and your pgn will be magically available in the am
    - restarting interrupted jobs, so if it detects that it's already downloaded the html, it will use the local copy instead.  Just issue the same command and it will scan its local cache as needed
      - This means that if variations get added to your course, you likely need to delete the course and/or chapter files for that course. (chapters are defined from the course file, and variations from the chapter files...).
      - This also means that if variations change (but keep the same id - no idea if this ever actually happens), then deleting that variation file and rerunning the course will cause that variation (only) to be repulled and processed. 
- All PGN is generated from scratch on every run, so the `<courseID>.pgn` file always contains all variations, in course order. 
- The good news is that once it's cached locally, if you need to rerun the PGN generator, it takes almost no time per page...
  - As the tool improves and the PGN is more useful, you can use the `pgn` option to just rerender the PGN from your cached html files. 
- The better news is that once I figure out how to properly multitask selenium, speed will improve.

Release Notes
- 
- v0.20 - 29-Apr-2025 - quantum improvement in capability, close to ready for prime-time
  - added the most basic possible interactive mode - the tool runs nicely from a desktop shortcut :)
  - changed default mode to incremental pgn generation in batch mode
  - fixed STR / PGN tags so they are more useful in ChessBase
  - cleanup of nested variations, including when they are "continuations"
  - better error reporting / exception handling
  - clean up this file (ReadMe.md) to be a little more readable and useful.
  - added `license.txt` file to reflect that this tool is covered by the MIT license.
- v0.11 - 28-Apr-2025
  - First pass at handling move and board eval NAGs as well as game results (so inconsistent in courses)
  - much closer to release-ready
  - Generally handles (properly) nested variations well.  The two edge cases I know of that still mess it up are
    - noted that occasionally the first move of a variation is a continuation, not an alternate move as defined in the spec, which correctly breaks PGN readers (including ChessBase).  The fix would be to re-enter the last move before the variation started
    - as mentioned before, also within a variation is repeated.  "g4 wins like this: g4 ..."  The fix here would be to not emit the second move.
    - the problem is I've tried hard NOT to keep game state or validate positions, since that's so heavyweight.  Will see if there's a quick fix 
      - would keeping the last emitted FEN be good enough for this?  Not formally, there could be N nested "continuations", but that's not the usage I've seen... will try it out
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

Open Items
- 
- Repeated moves in variation (very rare situation, 0 cases found across 8 full courses in testing)
- Better data / STR tag mapping so they are useful on ChessBase import
- multiprocessing support is broken
- ... unbelievably I think that's it...
- if you find something, fix it and send a pull request.  Email (below) may not be replied to in a timely manner...

Testing and Obvious Notes
-
- To test this, I would start with one variation from a small course so that you can establish that the tool is setup 
correctly.  I've tried to explain how to do that, but there's no support, warranty or other channel to help you if you
have trouble, except maybe Reddit.  Good luck.
  - (you can try email to chess at demastri dot com if you're really stuck, but it isn't regularly monitored)
- After running the tool and possibly stopping it prematurely, the tool occasionally returned 
`error in loadHtmlFromWeb for <"+url+"> on attempt 1-3`, failing after 3 attempts.  
  - Before looking at anything in the code, check that there are no instances of `Chrome for Testing` 
  running in Task Manager (on Windows).
  - A known issue with Selenium (and the reason for the Chrome for Testing browser):
    - it fails if more than one browser process is running or if more than one session in that process attempts to write
    to the same profile.  Check this first if you start seeing errors. 
    - you could use your "normal" Chrome install, but you'd have to be sure all other Chrome processes are killed first, 
    and you can't use it while the tool is running.  That stinks.  Use the Chrome for Testing browser. 
- This tool is intended to let you get more utility from ONLY the courses YOU have access to so that you can better utilize content you already 
own (think: use a version of your 1 e4 rep course in SCID or Chessbase).  This is why YOU have to set up the browser with your
chessable credentials.  Good luck with better leveraging of your rep in correspondence games, etc...
- It is NOT intended to help share content you don't already own. If you're sharing chessable credentials, or
sharing the output of the tool with people that don't have access, you're violating chessable's terms of service, and just
making the world a worse place, overall.  You're why we can't have nice things.  Kill yourself.
- It is a consequence of modern development that this file is larger (in overall size) than any of the code files in the repo...
- This code is (c) 2025 John DeMastri, usage is covered by the MIT License, see the License.txt file for your rights and obligations.
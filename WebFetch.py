#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: WebFetch.py
Author: John DeMastri
Create Date: 2025-04-27
Version: 0.3
Description: This script handles requests for HTML files.  Invokes selenium and caches files locally.
Based on config, it will utilize existing cached files before retrieving from the web.
Course files contain information on how to locate chapters.  Chapter files contain information on how to locate
variations.  Variations contain actual course data.  This file only parses metadata to locate other files.  Retrieving
actual course content from variations is handled in Pgn.py.

License: MIT License
Contact: chess@demastri.com
"""
import os.path
from pathlib import Path
import bs4
from selenium import webdriver
from selenium.webdriver import ActionChains
from bs4 import BeautifulSoup
import time

from selenium.webdriver.common.by import By

import ConfigData


class WebFetch:
    FETCH_NEW = 0
    FETCH_ALL = 1
    FETCH_NONE = 2
    flagNames = ["update", "all", "none"]

    doFetch = FETCH_NEW

    def __init__(self):
        WebFetch.doFetch = WebFetch.FETCH_NEW

    @classmethod
    def getCourseDetail(cls, courseId: str, profileName: str):
        # should return a map of chapter IDs and chapter names
        # course information is located at /course/<courseID>.html, content in /course/<courseID>/
        # chapters are located at /course/<courseID>/<chapter number>.html
        # course variations are located at /course/<courseID>/variation/<variation ID>.html
        # individual variations are located at /variation/<variationID>.html
        # pgn is only written for variations.
        # getting course detail amounts to:
        #  getting the metadata about the course from the course info file (name, author, ??)
        #  getting the list of chapters associated with this course
        #  for each chapter in the course
        #   getting the metadata about the chapter (name, priority, ??)
        #   getting the list of variations associated with this chapter
        #   for each variation in the chapter
        #    getting the detailed html for this variation
        #    generate the pgn for this detailed html (this is done elsewhere)
        #    do something with the pgn (this is done elsewhere)

        bs = WebFetch.getCourseHtml(courseId, profileName)
        if bs is None:
            return None, []
        chapters = WebFetch.getCourseChapters(bs)

        return bs, chapters

    @classmethod
    def getChapterDetail(cls, courseId: str, chapterBs: bs4.element.Tag, profileName: str):
        href = chapterBs.find('a', href=True)['href']
        tags = href.split('/')
        chapterID = tags[len(tags) - 1]
        bs = WebFetch.getChapterHtml(courseId, chapterID, profileName)
        variations = WebFetch.getChapterVariations(bs)

        return bs, variations

    @classmethod
    def getCourseChapters(cls, bs: BeautifulSoup):
        chapters = bs.find_all("div", class_="chapter")
        return chapters

    @classmethod
    def getCourseName(cls, bs: BeautifulSoup):
        if bs is None:
            return "<No Course HTML Available>"
        name = bs.find("title").text[:-12]  # strip off the trailing " - Chessable" from the title
        return name

    @classmethod
    def getChapterVariations(cls, bs: BeautifulSoup):
        variations = bs.find_all("div", class_="variation-card__row--main")
        return variations

    @classmethod
    def getChapterName(cls, tag: bs4.element.Tag):
        name = tag.find('div', class_="toBeClamped title").text
        return name

    @classmethod
    def getVariationDetailFromTag(cls, courseId: str, variationBs: bs4.element.Tag, profileName: str):
        name = variationBs.find('a', href=True).text
        href = variationBs.find('a', href=True)['href']
        tags = href.split('/')
        variationID = tags[len(tags) - 2]
        print("Getting Variation Detail '" + courseId + "-" + variationID + "-" + name + "'")
        bs = WebFetch.getVariationHtml(variationID, courseId, profileName)

        return [bs, variationID]

    @classmethod
    def getVariationDetailFromId(cls, courseId: str, variationID: str, profileName: str):
        bs = WebFetch.getVariationHtml(variationID, courseId, profileName)
        return [bs, variationID]

    @classmethod
    def getVariationHtml(cls, variationId: str, courseId: str, profileName: str):
        return WebFetch.getHtml("variation", variationId, profileName, "course/" + str(courseId), True)

    @classmethod
    def getVariationParts(cls, variationBs: bs4.element.Tag):
        if variationBs is None:
            return "", [], None, None, None
        try:
            name = variationBs.find('div', id="theOpeningTitle").text
            chapter = variationBs.find('div', class_="allOpeningDetails").find_all("li")
            moves = variationBs.find('div', id="theOpeningMoves").findChildren("span", recursive=False)
            term = variationBs.find('div', id="theOpeningMoves").findChildren("div", recursive=False)
            inputFEN = variationBs.find('input', id="inputFEN")["value"]
            return name, chapter, moves, term, inputFEN
        except:
            print("problem parsing variation parts\n")
            return "", [], None, None, None

    @classmethod
    def getChapterHtml(cls, courseId: str, chapterId: str, profileName):
        return WebFetch.getHtml("course", courseId + "/" + chapterId, profileName)

    @classmethod
    def getCourseHtml(cls, courseId: str, profileName: str):
        return WebFetch.getHtml("course", courseId, profileName)

    @classmethod
    def getHtml(cls, elementType, elementId: str, profileName: str, fileroot="", isVar=False):
        location = elementType
        if elementId != "":
            location += "/" + elementId
        url = ConfigData.BASE_CHESSABLE_URL + location
        if fileroot != "":
            location = fileroot + "/" + location

        # don't bother checking if we're overwriting all
        # if the file already exists, load it
        if WebFetch.doFetch == WebFetch.FETCH_ALL:
            pageHtml = WebFetch.loadHtmlFromWeb(url, profileName)
            WebFetch.writeHtmlToFile(location, pageHtml)
        else:
            pageHtml = WebFetch.loadHtmlFromFile(location)
            # otherwise get it from the web
            if len(pageHtml) == 0:
                if WebFetch.doFetch == WebFetch.FETCH_NONE:
                    return None
                # else doFetch == FETCH_NEW
                pageHtml = WebFetch.loadHtmlFromWeb(url, profileName, isVar)
                WebFetch.writeHtmlToFile(location, pageHtml)

        bs = None if pageHtml is None else BeautifulSoup(pageHtml, 'html.parser')
        return bs

    @classmethod
    def loadHtmlFromFile(self, location):
        if not os.path.exists(ConfigData.HTML_CACHE_PATH + location + ".html"):
            return ""
        with open(ConfigData.HTML_CACHE_PATH + location + ".html", "r", encoding='utf-8') as file:
            return file.read()

    @classmethod
    def writeHtmlToFile(self, location, content):
        path = Path(ConfigData.HTML_CACHE_PATH + location[:location.rfind("/")])
        path.mkdir(parents=True, exist_ok=True)
        with open(ConfigData.HTML_CACHE_PATH + location + ".html", "w", encoding='utf-8') as file:
            if content is None:
                print("-- returned no content from web")
            else:
                file.write(content)

    @classmethod
    def loadHtmlFromWeb(self, url, profileName, isVar=False):
        # print("Reading "+url+" using "+profileName)
        for retry in range(3):
            try:
                options = webdriver.ChromeOptions()
                options.add_argument('headless')
                options.binary_location = ConfigData.CHROME_FOR_TESTING_BINARY_LOC
                options.add_argument('--user-data-dir=' + ConfigData.TESTING_PROFILE_BASE_DIR)
                options.add_argument('--profile-directory=' + profileName)  # TESTING_PROFILE)
                browser = webdriver.Chrome(options=options)
                browser.get(url)
                time.sleep(2)
                if isVar:
                    controls = browser.find_element(By.ID, "controls")
                    buttons = controls.find_elements(By.TAG_NAME, "button")
                    backClass = buttons[1].get_attribute("class")
                    if not "myButtonOff" in backClass:
                        buttons[1].click()
                        time.sleep(1)
                outText = browser.page_source
                browser.quit()
                return outText
            except Exception as e:
                print("error in loadHtmlFromWeb for <" + url + "> on attempt :" + str(retry), end="")
                exception_message = e.args[0] if e.args else "No message"
                print(f": : {exception_message}")

        return None

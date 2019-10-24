import html
import os
import pprint
import re
import sys
import time

import requests
from dotenv import load_dotenv
from lxml.html import fromstring, tostring


class ZnOBrowser:
    """ZnO browser that handles login."""
    def __init__(self):

        load_dotenv()
        self.baseURL = "https://www.mrskin.com"
        self.user = os.getenv("MRSKIN_USER")
        self.pw = os.getenv("MRSKIN_PW")
        self.headers = {
            'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.90 Safari/537.36',
        }
        self.session = None

    def setSession(self, session):
        """Sets a new session."""
        self.session = session

    def getPage(self, path):
        """Gets HTML tree."""

        url = self.baseURL + path
        if self.session:
            response = self.session.get(url, headers=self.headers)
        else:
            response = requests.get(url, headers=self.headers)

        code = response.status_code
        # TODO if 429 (too many requests) inspect the Retry-after header to
        # sleep and try again
        if code != 200:
            print(response.headers)
            raise Exception(f"Request not succesful. Status: {code}")
        tree = fromstring(response.content)
        path = response.url.split(self.baseURL)[1]
        return {"path": path, "tree": tree}

    def login(self):
        """Logs in."""
        if not self.session:
            raise Exception("No session found. use setSession.")

        path = "/account/login"
        xml = self.getPage(path)["tree"]
        try:
            token = xml.xpath(
                "//input[@name='authenticity_token']")[0].attrib["value"]
        # TODO find out what error keeps throwing
        except:
            print(tostring(xml))
            raise

        payload = {
            "authenticity_token": token,
            "customer[username]": self.user,
            "customer[password]": self.pw,
        }

        url = self.baseURL + path
        self.session.post(url, data=payload, headers=self.headers)


def _extractRegex(regex, text):

    m = re.search(regex, text)
    return {
        "groups": m.groups(),
        "remainder": text.replace(m[0], "")
    } if m else {
        "groups": [],
        "remainder": text
    }


def getInfo(query, *args, **kwargs):
    """This will return the information of a title from a search term."""

    info = {}
    browser = ZnOBrowser()

    xml = browser.getPage("/search/titles?term=" + query)["tree"]
    titles = xml.xpath('//div[@class="thumbnail title"]')
    if titles == []:
        raise Exception("No titles found")

    # pick the first one
    titlePath = titles[0].xpath('./div/a')[0].attrib["href"]
    info["imgSrc"] = titles[0].xpath('./div/a/img')[0].attrib["data-src"]

    titlePage = browser.getPage(titlePath)
    titlePath = titlePage["path"]
    xml = titlePage["tree"]

    severityOptions = ["N/A", "Nude", "Sexy", "Nude - Body Double"]
    keywordOptions = [
        "butt", "breasts", "body double", "underwear", "prosthetic", "lesbian",
        "thong", "bush", "merkin"
    ]
    info["people"] = []
    safe = True
    times = set([])

    with requests.Session() as s:
        browser.setSession(s)
        browser.login()

        # print(tostring(xml))
        # TODO this isn't quite right, "Magicians" breaks it
        try:
            info["title"] = xml.xpath(
                '//div[@class="featured-scene-description"]//a[@class="title"]/text()'
            )[0]
        except IndexError:
            info["title"] = "Unknown"

        # get all title characters info
        chars = xml.xpath(
            '//div[@id="celebs-section"]//p[@class="h5 appearance-character"]')
        if chars == []:
            print(tostring(xml))
            raise Exception("Something went wrong, HTML may have changed")
        for char in chars:
            nodes = char.xpath('./*')
            if len(nodes) == 0:
                name = "Unknown"
                severity = "N/A"
            elif len(nodes) == 1:
                name = nodes[0].text
                severity = "N/A"
            elif len(nodes) == 2:
                name = nodes[1].text
                severity = nodes[0].text
            else:
                continue
            celeb = char.xpath('..//a')[0].text
            print(celeb)

            if severity not in severityOptions:
                print(tostring(char))
                raise Exception(
                    f"Severity \"{severity}\" not found, can't decide if it's safe."
                )

            # add more info if nude scenes
            scenes = []
            if "Nude" in severity:
                if kwargs["verbose"]:

                    safeKeywords = ["butt", "underwear", "thong"]

                    celebPath = char.xpath(
                        '..//a')[0].attrib["href"] + "/nude_scene_guide"

                    # TODO "the boys" breaks this
                    xml = browser.getPage(celebPath)["tree"]
                    media = xml.xpath(
                        f'//a[@href="{browser.baseURL + titlePath}"]/..//div[@class="media-body"]'
                    )
                    if len(media) < 1:
                        print(tostring(xml))
                        raise Exception(
                            "Something went wrong, may not be logged in.")

                    print(
                        f"{len(media)} {'scene' if len(media) == 1 else 'scenes'}"
                    )
                    for scene in media:
                        scenes.append({})
                        time.sleep(2)
                        keywords = scene.xpath(
                            './/span[@class="scene-keywords"]//span[@class="text-muted"]//text()'
                        )[0].split(",")
                        keywords = list(map(lambda x: x.strip(), keywords))
                        for keyword in keywords:
                            if keyword not in keywordOptions:
                                raise Exception(
                                    f"Keyword \"{keyword}\" not found, can't decide if it's safe."
                                )
                            if keyword not in safeKeywords:
                                safe = False

                        description = scene.xpath(
                            './/span[@class="scene-description"]//text()')
                        description = "".join(description).strip()
                        print(description)
                        text = _extractRegex(r"(\d+:\d+:\d+)", description)
                        start = "Unknown"
                        if len(text["groups"]) > 0:
                            start = text["groups"][0]
                        text = _extractRegex(r"\((.*(min|sec).*)\)",
                                             text["remainder"])
                        duration = text["groups"][0]
                        text = _extractRegex(r"Ep. (\d+)x(\d+) \|",
                                             text["remainder"])
                        if text["groups"]:
                            scenes[-1]["season"] = text["groups"][0]
                            scenes[-1]["episode"] = text["groups"][1]
                            times.add(
                                f"Ep {text['groups'][0]}x{text['groups'][1]} | {start}"
                            )
                        else:
                            if start != "Unknown":
                                times.add(f"{start}")
                        scenes[-1]["keywords"] = keywords
                        scenes[-1]["time"] = start
                        scenes[-1]["duration"] = duration
                        scenes[-1]["description"] = html.unescape(
                            text["remainder"].strip())

                else:
                    safe = False
                    break
            else:
                time.sleep(2)

            info["people"].append({
                "actor": celeb,
                "character": name,
                "severity": severity,
                "scenes": scenes
            })

    info["safe"] = safe
    info["times"] = sorted(times)
    return info


if __name__ == "__main__":
    pprint.pprint(getInfo(sys.argv[1], verbose=True))

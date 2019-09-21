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


def _extract(regex, text):

    m = re.search(regex, text)
    if m:
        groups = m.groups()
        text = text.replace(m[0], "")
    else:
        groups = None
    return [groups, text]


def getInfo(query):
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
    info["title"] = titles[0].xpath(
        './/div[@class="caption"]/a')[0].attrib["title"]

    titlePage = browser.getPage(titlePath)
    titlePath = titlePage["path"]
    xml = titlePage["tree"]

    severityOptions = ["N/A", "Nude", "Sexy", "Nude - Body Double"]
    keywordOptions = [
        "butt", "breasts", "body double", "underwear", "prosthetic", "lesbian",
        "thong", "bush"
    ]
    info["people"] = []
    safe = True
    episodes = set([])

    with requests.Session() as s:
        browser.setSession(s)
        browser.login()

        # get all title characters info
        chars = xml.xpath(
            '//div[@id="celebs-section"]//p[@class="h5 appearance-character"]')
        if chars == []:
            raise Exception("Something went wrong, HTML may have changed")
        for char in chars:
            nodes = char.xpath('./*')
            if len(nodes) < 2:
                name = nodes[0].text
                severity = "N/A"
            else:
                name = nodes[1].text
                severity = nodes[0].text
            celeb = char.xpath('..//a')[0].text
            print(celeb)

            if severity not in severityOptions:
                raise Exception(
                    "Severity not found, can't decide if it's safe.\n" +
                    str(tostring(char)))

            # TODO adjustable
            maxSafeMode = False

            # add more info if nude scenes
            scenes = []
            if "Nude" in severity:
                if not maxSafeMode:

                    safeKeywords = ["butt"]

                    celebPath = char.xpath(
                        '..//a')[0].attrib["href"] + "/nude_scene_guide"

                    xml = browser.getPage(celebPath)["tree"]
                    media = xml.xpath(
                        f'//a[@href="{browser.baseURL + titlePath}"]/..//div[@class="media-body"]'
                    )
                    if len(media) < 1:
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
                                    f"Keyword \"{keyword}\" not found, can't decide if it's safe.\n"
                                )
                            if keyword not in safeKeywords:
                                safe = False

                        description = scene.xpath(
                            './/span[@class="scene-description"]//text()')
                        description = "".join(description).strip()
                        print(description)
                        text = _extract(r"(\d+:\d+:\d+)", description)
                        start = text[0][0]
                        text = _extract(r"\((\d.*secs)\)", text[1])
                        duration = text[0][0]
                        text = _extract(r"Ep. (\d+)x(\d+) \|", text[1])
                        if text[0]:
                            scenes[-1]["season"] = text[0][0]
                            scenes[-1]["episode"] = text[0][1]
                            episodes.add(f"Ep {text[0][0]}x{text[0][1]}")
                        scenes[-1]["keywords"] = keywords
                        scenes[-1]["time"] = start
                        scenes[-1]["duration"] = duration
                        scenes[-1]["description"] = html.unescape(
                            text[1].strip())

                else:
                    safe = False
            else:
                time.sleep(2)

            info["people"].append({
                "actor": celeb,
                "character": name,
                "severity": severity,
                "nude scenes": scenes
            })

    info["safe"] = safe
    if len(episodes):
        info["episodes"] = sorted(episodes)
    return info


if __name__ == "__main__":
    pprint.pprint(getInfo(sys.argv[1]))

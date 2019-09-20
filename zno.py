import os
import pprint

import requests
from dotenv import load_dotenv
from lxml import html

load_dotenv()

baseURL = "https://www.mrskin.com"

headers = {
    'User-Agent':
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.90 Safari/537.36',
}


class ZnOBrowser:
    """ZnO browser that handles login."""
    def __init__(self):

        load_dotenv()
        self.baseURL = "https://mrskin.com"
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

    def getTree(self, url):
        """Gets HTML tree."""

        fullURL = baseURL + url
        if self.session:
            return html.fromstring(
                self.session.get(fullURL, headers=self.headers).content)
        else:
            return html.fromstring(
                requests.get(fullURL, headers=self.headers).content)

    def login(self):
        """Logs in."""
        if not self.session:
            raise Exception("No session found. use setSession.")

        loginURL = "/account/login"
        tree = self.getTree(loginURL)
        token = tree.xpath(
            "//input[@name='authenticity_token']")[0].attrib["value"]

        payload = {
            "utf8": "✓",
            "_tgt_url": "/",
            "authenticity_token": token,
            "customer[username]": self.user,
            "customer[password]": self.pw,
            "customer[remember_me]": "0",
            "commit": "Please Sign In",
        }

        self.session.post(loginURL, data=payload, headers=headers)


def _login():

    with requests.Session() as session:

        loginURL = baseURL + "/account/login"
        response = session.get(loginURL, headers=headers)
        loginPage = html.fromstring(response.content)
        token = loginPage.xpath(
            "//input[@name='authenticity_token']")[0].attrib["value"]
        user = os.getenv("MRSKIN_USER")
        pw = os.getenv("MRSKIN_PW")

        payload = {
            "utf8": "✓",
            "_tgt_url": "/",
            "authenticity_token": token,
            "customer[username]": user,
            "customer[password]": pw,
            "customer[remember_me]": "0",
            "commit": "Please Sign In",
        }

        session.post(loginURL, data=payload, headers=headers)
        return session


def _request(url, auth=False):

    if not auth:
        return requests.get(url, headers=headers)

    s = _login()
    response = s.get(url, headers=headers)
    return response


def getInfo(query, session=None):
    """This will return the information of a title from a search term."""

    info = {}

    browser = ZnOBrowser()
    searchPage = browser.getTree("/search/titles?term=" + query)
    # searchURL = baseURL + "/search/titles?term=" + query
    # searchPage = html.fromstring(_request(searchURL).content)
    titles = searchPage.xpath('//div[@class="thumbnail title"]')
    if titles == []:
        raise Exception("No titles found")

    # pick the first one
    titleURL = baseURL + titles[0].xpath('./div/a')[0].attrib["href"]
    info["imgSrc"] = titles[0].xpath('./div/a/img')[0].attrib["data-src"]
    info["title"] = titles[0].xpath(
        './/div[@class="caption"]/a')[0].attrib["title"]

    response = _request(titleURL)
    titleURL = response.url.split(baseURL)[1]
    titlePage = html.fromstring(response.content)

    # get all title characters info
    chars = titlePage.xpath(
        '//div[@id="celebs-section"]//p[@class="h5 appearance-character"]')
    if chars == []:
        raise Exception("Something went wrong, HTML may have changed")
    info["people"] = []
    severityOptions = ["N/A", "Nude", "Sexy", "Nude - Body Double"]
    # TODO need to make this smaller
    keywordOptions = [
        "butt", "breasts", "breasts, body double", "breasts, butt",
        "butt, body double", "breasts, butt, body double"
    ]
    safe = True
    for char in chars:
        nodes = char.xpath('./*')
        if len(nodes) < 2:
            name = nodes[0].text
            severity = "N/A"
        else:
            name = nodes[1].text
            severity = nodes[0].text
        celeb = char.xpath('..//a')[0].text

        if severity not in severityOptions:
            raise Exception(
                "Severity not found, can't decide if it's safe.\n" +
                str(html.tostring(char)))

        # TODO adjustable
        fullSafeMode = False

        # add more info if nude scenes
        scenes = []
        if "Nude" in severity:
            if not fullSafeMode:

                # TODO adjustable
                safeKeywords = ["butt"]

                celebURL = baseURL + char.xpath(
                    '..//a')[0].attrib["href"] + "/nude_scene_guide"
                response = _request(celebURL, True)
                celebPage = html.fromstring(response.content)
                media = celebPage.xpath(
                    f'//a[@href="{baseURL + titleURL}"]/..//div[@class="media-body"]'
                )
                if len(media) < 1:
                    raise Exception(
                        "Something went wrong, may not be logged in.")

                for scene in media:
                    keywords = scene.xpath(
                        './/span[@class="scene-keywords"]//span[@class="text-muted"]//text()'
                    )[0]
                    if keywords not in keywordOptions:
                        raise Exception(
                            f"Keyword \"{keywords}\" not found, can't decide if it's safe.\n"
                        )
                    if keywords not in safeKeywords:
                        safe = False

                    # TODO pull out episode and time but leave out description
                    # they seem too explicit
                    description = scene.xpath(
                        './/span[@class="scene-description"]//text()')
                    scenes.append({
                        "keywords": keywords,
                        "description": "".join(description).strip()
                    })

            else:
                safe = False

        info["people"].append({
            "actor": celeb,
            "character": name,
            "severity": severity,
            "nude scenes": scenes
        })

    info["safe"] = safe
    return info


if __name__ == "__main__":
    pprint.pprint(getInfo("fight club"))

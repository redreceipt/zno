import webbrowser
import os
import pprint
import re
import sys

import requests
from dotenv import load_dotenv
from lxml.html import fromstring, tostring


class XMLError(Exception):
    def __init__(self, path, message):
        webbrowser.get("chrome").open(path)
        super().__init__(message)


class ZnOBrowser:
    """ZnO browser that handles login."""

    base_url = "https://www.mrskin.com"
    user = os.getenv("MRSKIN_USER")
    pw = os.getenv("MRSKIN_PW")
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.90 Safari/537.36",
    }

    def __init__(self):

        load_dotenv()
        self.session = None

    def get_page(self, path):
        """Gets HTML tree."""

        url = self.base_url + path
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
        path = response.url.split(self.base_url)[1]
        return {"url": response.url, "path": path, "tree": tree}

    def login(self):

        login_page = self.get_page("/account/login")
        token = (
            login_page["tree"]
            .xpath("//input[@name='authenticity_token']")[0]
            .attrib["value"]
        )

        data = {
            "authenticity_token": token,
            "customer[username]": self.user,
            "customer[password]": self.pw,
        }

        r = self.session.post(login_page["url"], data=data, headers=self.headers)
        if r.status_code != 200:
            print(r)
            raise Exception("Login not succesful!")


def getInfo(query, *args, **kwargs):
    """This will return the information of a title from a search term."""

    info = {"people": [], "safe": True}
    browser = ZnOBrowser()

    # search for the title
    search_page = browser.get_page("/search/titles?term=" + query)
    titles = search_page["tree"].xpath('//div[@class="thumbnail title"]')
    if titles == []:
        return {}

    # pick the first one
    title_path = titles[0].xpath("./div/a")[0].attrib["href"]
    info["imgSrc"] = titles[0].xpath("./div/a/img")[0].attrib["data-src"]
    info["title"] = titles[0].xpath('//div[@class="caption"]/a')[0].attrib["title"]

    # go to the title page
    title_page = browser.get_page(title_path)

    severityOptions = ["N/A", "Nude", "Sexy", "Nude - Body Double"]
    keywordOptions = [
        "bikini",
        "butt",
        "breasts",
        "body double",
        "underwear",
        "prosthetic",
        "lesbian",
        "thong",
        "bush",
        "merkin",
    ]
    safe_keyword_options = ["butt", "underwear", "thong", "bikini"]
    times = set([])

    with requests.Session() as s:
        browser.session = s
        browser.login()

        # get all title characters info
        chars = title_page["tree"].xpath(
            '//div[@id="celebs-section"]//p[@class="h5 appearance-character"]'
        )
        if chars == []:
            raise XMLError(title_page["url"], "Can't find characters in the title!")

        for char in chars:
            nodes = char.xpath("./*")
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
            celeb = char.xpath("..//a")[0].text

            if severity not in severityOptions:
                raise Exception(
                    f"Severity \"{severity}\" not found, can't decide if it's safe."
                )

            # add more info if nude scenes
            scenes = []
            if "Nude" in severity:
                if kwargs["verbose"]:

                    celeb_path = (
                        char.xpath("..//a")[0].attrib["href"] + "/nude_scene_guide"
                    )

                    celeb_page = browser.get_page(celeb_path)
                    # TODO sometimes scenes don't show up here on the free account
                    celeb_scenes = celeb_page["tree"].xpath(
                        f'//a[@href="{title_path}"]/../../../..//div[@class="media-body"]'
                    )

                    for scene in celeb_scenes:
                        scenes.append({})
                        keywords = scene.xpath(
                            './/span[@class="scene-keywords"]//span[@class="text-muted"]//text()'
                        )[0].split(",")
                        for keyword in [word.strip() for word in keywords]:
                            if keyword not in keywordOptions:
                                raise Exception(
                                    f"Unknown keyword \"{keyword}\", can't decide if it's safe."
                                )
                            if keyword not in safe_keyword_options:
                                info["safe"] = False

                        description = scene.xpath(
                            './/span[@class="scene-description"]//text()'
                        )
                        description = "".join(description).strip()

                        # start time
                        m = re.search(r"(\d+:\d+:\d+)", description)
                        start = m.group() if m else "Unknown"
                        description = (
                            description.replace(start, "") if m else description
                        )

                        # scene duration
                        m = re.search(r"\((.*(min|sec).*)\)", description)
                        duration = m.group() if m else "Unknown"
                        description = (
                            description.replace(duration, "") if m else description
                        )

                        m = re.search(r"Ep. (\d+)x(\d+) \|", description)
                        tv = m.groups() if m else None
                        if tv:
                            scenes[-1]["season"] = tv[0]
                            scenes[-1]["episode"] = tv[1]
                            times.add(f"Ep {tv[0]}x{tv[1]} | {start}")
                            description = description.replace(
                                f"Ep. {tv[0]}x{tv[1]} |", ""
                            )

                        # movie
                        else:
                            if start != "Unknown":
                                times.add(f"{start}")
                        scenes[-1]["keywords"] = [word.strip() for word in keywords]
                        scenes[-1]["time"] = start
                        scenes[-1]["duration"] = duration
                        scenes[-1]["description"] = description.strip()

                else:
                    info["safe"] = False
                    break

            info["people"].append(
                {
                    "actor": celeb,
                    "character": name,
                    "severity": severity,
                    "scenes": scenes,
                }
            )

    info["times"] = sorted(times)
    return info


if __name__ == "__main__":
    pprint.pprint(getInfo(sys.argv[1], verbose=True))

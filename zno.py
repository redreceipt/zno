import pprint

import requests
from lxml import html

baseURL = "https://www.mrskin.com"


def _request(url, auth=False):

    headers = {
        'User-Agent':
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.90 Safari/537.36',
    }
    if not auth:
        return requests.get(url, headers=headers)

    creds = {"customer[username]": "USER", "customer[password]": "PASS"}
    with requests.Session() as session:
        post = session.post(baseURL + "/account/login",
                            data=creds,
                            headers=headers)
        print(post.text)
        response = session.get(baseURL + url, headers=headers)

    return response


def getInfo(title, session=None):
    """This will return the information of a title from a search term."""

    info = {}

    searchURL = baseURL + "/search/titles?term=" + title
    searchPage = html.fromstring(_request(searchURL).content)
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

        # add more info if nude scenes
        scenes = []
        # TODO: once I figure out auth
        '''
        if "Nude" in severity:
            celebURL = baseURL + char.xpath(
                '..//a')[0].attrib["href"] + "/nude_scene_guide"
            response = _request(celebURL, True)
            celebPage = html.fromstring(response.content)
            media = celebPage.xpath(
                f'//a[@href="{titleURL}"]/..//div[@class="media-body"]')
            print(html.tostring(media[0]))
            raise Exception
            for scene in media:
                keywords = scene.xpath(
                    './/span[@class="scene-keywords"]//text()')
                description = scene.xpath(
                    './/span[@class="scene-description"]//text()')
                scenes.append({
                    "keywords": "".join(keywords),
                    "description": "".join(description)
                })
        '''

        info["people"].append({
            "actor": celeb,
            "character": name,
            "severity": severity,
            "nude scenes": scenes
        })
        if severity not in ["N/A", "Nude", "Sexy", "Nude - Body Double"]:
            raise Exception(
                "Something went wrong, can't decide if it's safe.\n" +
                str(html.tostring(char)))
        if severity == "Nude":
            safe = False

    info["safe"] = safe
    return info


if __name__ == "__main__":
    pprint.pprint(getInfo("lucifer"))

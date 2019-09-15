import requests
from lxml import html


def _safeRequest(url):

    headers = {
        'User-Agent':
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.90 Safari/537.36'
    }
    return requests.get(url, headers=headers)


def getInfo(title):
    """This will return the information of a title from a search term."""

    info = {}
    baseURL = "https://www.mrskin.com"
    url = baseURL + "/search/titles?term=" + title
    response = _safeRequest(url)

    searchPage = html.fromstring(response.content)
    titles = searchPage.xpath('//div[@class="thumbnail title"]')
    if titles == []:
        raise Exception("No titles found")

    # pick the first one
    titleURL = baseURL + titles[0].xpath('./div/a')[0].attrib["href"]
    info["imgSrc"] = titles[0].xpath('./div/a/img')[0].attrib["data-src"]
    info["title"] = titles[0].xpath(
        './/div[@class="caption"]/a')[0].attrib["title"]

    response = _safeRequest(titleURL)
    titlePage = html.fromstring(response.content)
    chars = titlePage.xpath(
        '//div[@id="celebs-section"]//p[@class="h5 appearance-character"]')
    if chars == []:
        raise Exception("Something went wrong, HTML may have changed")
    for char in chars:
        nodes = char.xpath('./*')
        severity = nodes[0].text.lower()
        if severity not in ["nude", "sexy"]:
            raise Exception(
                "Something went wrong, can't decide if it's safe.\n" +
                html.tostring(nodes[0]))
        if severity == "nude":
            info["safe"] = False
        else:
            info["safe"] = True
        return info


if __name__ == "__main__":
    print(getInfo("gladiator"))

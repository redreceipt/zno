import requests
from lxml import html


def _safeRequest(url):

    headers = {
        'User-Agent':
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.90 Safari/537.36'
    }
    return requests.get(url, headers=headers)


def isTitleSafe(title):
    """This will return the information of a title from a search term."""

    baseURL = "https://www.mrskin.com"
    url = baseURL + "/search/titles?term=" + title
    response = _safeRequest(url)

    searchPage = html.fromstring(response.content)
    titles = searchPage.xpath('//div[@class="thumbnail-image "]/a')
    if titles == []:
        raise Exception("No titles found")

    # pick the first one
    titleURL = baseURL + titles[0].attrib["href"]
    # TODO: also return title image to verify it's the right one
    response = _safeRequest(titleURL)
    titlePage = html.fromstring(response.content)
    chars = titlePage.xpath(
        '//div[@id="celebs-section"]//p[@class="h5 appearance-character"]')
    if chars == []:
        raise Exception("Something went wrong, HTML may have changed")
    for char in chars:
        print(html.tostring(char))
        nodes = char.xpath('./*')
        severity = nodes[0].text.lower()
        if severity not in ["nude", "sexy"]:
            print(html.tostring(nodes[0]))
            raise Exception("Something went wrong, can't decide if it's safe.")
        if severity == "nude":
            return False
    return True

    # nudeCharacters = titlePage.xpath(
    # '//p[@class="h5 appearance-character"]/span[@class="text-danger"]')
    # if nudeCharacters != []:
    # return False
    # return True


if __name__ == "__main__":
    print(isTitleSafe("knocked up"))

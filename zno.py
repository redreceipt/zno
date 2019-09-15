import requests
import xml.etree.ElementTree as ET

def getTitle(term):
    """This will return the information of a title from a search term."""
    res = requests.get("https://www.mrskin.com/search/title?term=" + term)
    print(res)

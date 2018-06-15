from bs4 import BeautifulSoup
from user_agent import generate_user_agent
import requests
import json

item_url_names = []

def mean(items):
    return sum(items) / len(items)


def get_items():
    items_api = 'https://api.warframe.market/v1/items/'
    response = requests.get(items_api)
    datastore = response.json()
    print datastore
    for item in datastore["payload"]["items"]["en"]:
        item_url_names.append(item["url_name"])


def format_item_statistics_api(url_name):
    return 'https://api.warframe.market/v1/items/' + url_name + '/statistics/'


def find_arbitrage():
    average_vols = []
    for item in item_url_names:
        statistics_api = format_item_statistics_api(item)
        response = requests.get(statistics_api)
        datastore = response.json()
        item_volatilities = [day["volume"] for day in datastore["payload"]["statistics"]["90days"]]
        average_vol = mean(item_volatilities)
        item_vol = {
            'item': item,
            'vol': average_vol
        }
        average_vols.append(item_vol)
    average_vols = sorted(avarege_vols, key=lambda k: k['vol'])  
    print average_vols


get_items()
find_arbitrage()

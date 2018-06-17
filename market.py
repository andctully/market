import json
import os
import pickle
import requests
import statistics
import time

ITEM_URL_NAMES_FILE = 'item_url_names'
ITEM_HIST_STATS_FILE = 'item_hist_stats'
GET_ITEMS_API = 'https://api.warframe.market/v1/items'

item_url_names = []         # url names of items for api calls
item_hist_stats = {}   # historical item statistics

ITEM_MARKET_WATCH = [
    {
        'url_name': 'rifle_riven_mod_(veiled)',
        'buy_price': 45,
        'sell_price': 58
    },
    {
        'url_name': 'shotgun_riven_mod_(veiled)',
        'buy_price': 85,
        'sell_price': 110
    },
    {
        'url_name': 'pistol_riven_mod_(veiled)',
        'buy_price': 15,
        'sell_price': 30
    },
    {
        'url_name': 'melee_riven_mod_(veiled)',
        'buy_price': 25,
        'sell_price': 35
    }
]

def get_json_from_api(api_call):
    return requests.get(api_call).json()


def get_item_url_names():
    global item_url_names
    if os.path.exists(ITEM_URL_NAMES_FILE):
        with open(ITEM_URL_NAMES_FILE, 'rb') as f:
            item_url_names = pickle.load(f)
    if not item_url_names:
        datastore = get_json_from_api(GET_ITEMS_API)
        for item in datastore["payload"]["items"]["en"]:
            item_url_names.append(item["url_name"])
        with open(ITEM_URL_NAMES_FILE, 'wb') as f:
            pickle.dump(item_url_names, f, pickle.HIGHEST_PROTOCOL)


def format_item_statistics_api(url_name):
    return '/'.join([GET_ITEMS_API, url_name, 'statistics'])

def format_item_orders_api(url_name):
    return '/'.join([GET_ITEMS_API, url_name, 'orders'])


def get_item_statistics():
    global item_hist_stats
    if os.path.exists(ITEM_HIST_STATS_FILE):
        with open(ITEM_HIST_STATS_FILE, 'rb') as f:
            item_hist_stats = pickle.load(f)
    if not item_hist_stats:
        counter = 0
        for url_name in item_url_names:
            statistics_api = format_item_statistics_api(url_name)
            datastore = get_json_from_api(statistics_api)
            stats_90_days = datastore['payload']['statistics']['90days']

            open_prices = []
            closed_prices = []
            moving_avgs = []
            medians = []
            avg_prices = []
            min_prices = []
            max_prices = []
            volumes = []

            for day in stats_90_days:
                for key, value in day.items():
                    if key == 'open_price': open_prices.append(value)
                    if key == 'closed_price': closed_prices.append(value)
                    if key == 'moving_avg': moving_avgs.append(value)
                    if key == 'median': medians.append(value)
                    if key == 'avg_price': avg_prices.append(value)
                    if key == 'min_price': min_prices.append(value)
                    if key == 'max_price': max_prices.append(value)
                    if key == 'volume': volumes.append(value)

            item_hist_stats[url_name] = {
                'open_prices': open_prices,
                'closed_prices': closed_prices,
                'moving_avgs': moving_avgs,
                'medians': medians,
                'avg_prices': avg_prices,
                'min_prices': min_prices,
                'max_prices': max_prices,
                'volumes': volumes
            }
            counter += 1
            print '(' + str(counter) + '/' + str(len(item_url_names)) + ') Item Stats Obtained'

        with open(ITEM_HIST_STATS_FILE, 'wb') as f:
            pickle.dump(item_hist_stats, f, pickle.HIGHEST_PROTOCOL)


def get_online_orders(url_name):
    item_orders_api = format_item_orders_api(url_name)
    json = get_json_from_api(item_orders_api)
    orders = json['payload']['orders']
    buyers = []
    sellers = []
    for order in orders:
        user = order['user']
        if user['status'] != 'ingame' or order['platform'] != 'pc': 
            continue
        if order['order_type'] == 'sell':
            sellers.append(order)
        elif order['order_type'] == 'buy':
            buyers.append(order)
    buyers = sorted(buyers, key=lambda k: k['platinum'], reverse=True) 
    sellers = sorted(sellers, key=lambda k: k['platinum'])
    ret = {
        'buyers': buyers,
        'sellers': sellers
    }
    return ret

def market_watch(): 
    orders_seen = {}
    while True:
        for item in ITEM_MARKET_WATCH:
            print 'Checking market for deals on ' + item['url_name'] + '...'
            if item['url_name'] not in orders_seen:
                orders_seen[item['url_name']] = {
                    'buyers': [],
                    'sellers': []
                }
            item_orders = orders_seen[item['url_name']]
            orders = get_online_orders(item['url_name'])
    
            # Determines if an order has been seen before or not
            def is_new_order(order):
                if order['order_type'] == 'buy':
                    for buyer in orders_seen[item['url_name']]['buyers']:
                        if  buyer['user']['ingame_name'] == order['user']['ingame_name'] and \
                            buyer['platinum'] == order['platinum']:
                                return False
                else:
                    for seller in orders_seen[item['url_name']]['sellers']:
                        if  seller['user']['ingame_name'] == order['user']['ingame_name'] and \
                            seller['platinum'] == order['platinum']:
                                return False
                return True

            # Check if any new orders are good deals
            for buyer in orders['buyers']:
                if is_new_order(buyer)  and buyer['platinum'] >= item['sell_price']:
                    print_order(item['url_name'], buyer)
            for seller in orders['sellers']:
                if is_new_order(seller) and seller['platinum'] <= item['buy_price']:
                    print_order(item['url_name'], seller)
            
            # Update to current orders
            orders_seen[item['url_name']]['buyers'] = orders['buyers']
            orders_seen[item['url_name']]['sellers'] = orders['sellers']

            # Print current price statistics
            highest_buy_price = orders['buyers'][0]['platinum']
            lowest_sell_price = orders['sellers'][0]['platinum']
            print '{} | Highest buyer: {} platinum \t Lowest Seller: {} platinum'.format(
                    item['url_name'], highest_buy_price, lowest_sell_price)
            print ''
        
        print 'Sleeping for 20 seconds...'
        time.sleep(20)



def print_order(item, order):    
    print '%%%%-----------------------------------%%%%'
    if order['order_type'] == 'sell':
        print '{} is selling {}x of {} for {} platinum!'.format(order['user']['ingame_name'], order['quantity'], item, order['platinum'])
    else:
        print '{} is buying {}x of {} for {} platinum!'.format(order['user']['ingame_name'], order['quantity'],  item, order['platinum'])
    print '%%%%-----------------------------------%%%%'
    print ''


market_watch()

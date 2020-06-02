import requests


def get_price(stock_id):
    sid = {"sid": stock_id}
    resp = requests.get('http://127.0.0.1:5000/get_price', data=sid)
    if resp.status_code != 200:
        # This means something went wrong.
        raise Exception('GET /get_price/ {}'.format(resp.status_code))
    for todo_item in resp.json():
        print('{} {}'.format(todo_item['id'], todo_item['summary']))

import time

import requests

from ParserApp import ParserApp
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)


@app.route('/test', methods=['GET'])
def test():
    return "1"


@app.route('/parse_product_page', methods=['POST'])
def parse_product_page():
    res = parser_app.parse_product_page_full(request.json['url'], request.json['only_prices'])

    if res == -1:
        return "Server is too busy now, can't reply"

    return str(res)


@app.route('/parse_product_page_temp', methods=['POST'])
def parse_product_page_temp():
    res = parser_app.parse_product_page_full_temp(request.json['url'], request.json['only_prices'], request.json['i'])

    if res == -1:
        return "Server is too busy now, can't reply"

    return str(res)


if __name__ == '__main__':
    parser_app = ParserApp()

    static_proxies_list = list(map(lambda s: "http:" + s, open("proxies.txt").read().strip().split()))

    parser_app.start(number_of_static_profiles=1, number_of_dynamic_profiles=1,
                     dynamic_proxies_list=[
                         "http:188.143.169.27:30138:iparchitect_28044_06_08_23:d6YQZ7SnFTyd5Tnise"
                     ],
                     static_proxies_list=static_proxies_list)

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

import time

import requests

from parser_app import ParserApp
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

    parser_app.start(number_of_profiles=1, proxy_list=["http:46.8.23.126:1050:uDl4HM:6ZdsY71cp7"])

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

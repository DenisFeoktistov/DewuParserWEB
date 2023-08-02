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


if __name__ == '__main__':
    parser_app = ParserApp()

    parser_app.start(number_of_profiles=1, proxy_list=["101.91.114.42:37634:EE244126:562F824E3199"])

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

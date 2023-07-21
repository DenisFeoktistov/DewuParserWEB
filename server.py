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

    get_proxy_url = "http://proxy.siyetian.com/apis_get.html?token=AesJWLNRUSx8ERJdXTq10dOpXS45keVRTTn1STqFUeNpXQz0EVrNjTU10dNpWWx0keFJzTUVUM.AOxEzN4gTO4YTM&limit=10&type=0&time=&split=2&split_text=&repeat=0&isp=0"
    parser_app.start(number_of_profiles=5, get_proxy_url=get_proxy_url)

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

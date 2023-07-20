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

    current_proxy = "http:" + requests.request("GET", "http://proxy.siyetian.com/apis_get.html?token=AesJWLORUT65keJdXTq10dOpXS35ERrpnT31STqFUeNpXQz0EVrNjTU10dNpWWx0keFJzTUVUM.AM1MDN4gTO4YTM&limit=1&type=0&time=&split=2&split_text=&repeat=0&isp=0").text
    print(f"Current proxy: {current_proxy}")

    parser_app.start(number_of_profiles=1, proxy_list=[current_proxy])

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

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

    parser_app.start(number_of_profiles=1, proxy_list=
    [
        "http:188.143.169.27:30138:iparchitect_28044_06_08_23:d6YQZ7SnFTyd5Tnise",
        "http:188.143.169.27:30152:iparchitect_28044_06_08_23:d6YQZ7SnFTyd5Tnise",
        "http:188.143.169.27:30149:iparchitect_28044_06_08_23:d6YQZ7SnFTyd5Tnise",
        "http:188.143.169.27:30054:iparchitect_28044_06_08_23:d6YQZ7SnFTyd5Tnise",
        "http:188.143.169.27:30044:iparchitect_28044_06_08_23:d6YQZ7SnFTyd5Tnise",
        "http:188.143.169.27:30053:iparchitect_28044_06_08_23:d6YQZ7SnFTyd5Tnise",
        "http:188.143.169.27:30051:iparchitect_28044_06_08_23:kSib7DBKr9SssyyD64",
        "http:188.143.169.27:30014:iparchitect_28044_06_08_23:NDEyEfT8n24552t7Kt",
        "http:188.143.169.27:30038:iparchitect_28044_06_08_23:S3SAHreQHrQi8t4de4",
        "http:188.143.169.27:30043:iparchitect_28044_06_08_23:5f28QsnahK88Ht55hA"
    ])

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

import asyncio
import json
import random

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from ParserApp import ParserApp
from ParseRequests import ParseRequests
from Statuses import ErrorMessages

from logger import main_logger

app = FastAPI()
parser_app = ParserApp()


@app.get('/test')
async def test():
    return JSONResponse(status_code=200, content={"message": "1"})


@app.post('/parse_product_page')
async def parse_product_page_main(request: Request):
    main_logger.info(f"Parse product page main request {request.url, await request.json(), request.client}")

    data = await request.json()
    url = data['url']

    print("Parse product page request")
    print(*map(lambda b: b.status, parser_app.static_proxies_browsers),
          *map(lambda b: b.status, parser_app.dynamic_proxies_browsers))

    result = await parser_app.parse_product_page(url, ParseRequests.MAIN)

    if result in ErrorMessages.ALL:
        return JSONResponse(status_code=500, content={"message": result})

    return JSONResponse(status_code=200, content=result)


@app.post('/parse_product_page_passive')
async def parse_product_page_passive(request: Request):
    main_logger.info(f"Parse product page passive request {request.url, await request.json(), request.client}")

    data = await request.json()
    url = data['url']

    result = await parser_app.parse_product_page(url, ParseRequests.PASSIVE)

    if result in ErrorMessages.ALL:
        return JSONResponse(status_code=500, content={"message": result})

    return JSONResponse(status_code=200, content=result)


@app.post('/parse_product_page_aggressive')
async def parse_product_page_aggressive(request: Request):
    main_logger.info(f"Parse product page aggressive request {request.url, await request.json(), request.client}")

    data = await request.json()
    url = data['url']

    result = await parser_app.parse_product_page(url, ParseRequests.AGGRESSIVE)

    if result in ErrorMessages.ALL:
        return JSONResponse(status_code=500, content={"message": result})

    return JSONResponse(status_code=200, content=result)


@app.post('/reserve_parser_for_aggressive')
async def reserve_parser_for_aggressive():
    main_logger.info(f"Reserve parser for aggressive request")

    result = await parser_app.reserve_parser_for_aggressive()

    if result in ErrorMessages.ALL:
        return JSONResponse(status_code=500, content={"message": result})

    return JSONResponse(status_code=200, content={"message": "Browser has been reserved"})


@app.post('/release_parser_for_aggressive')
async def release_parser_for_aggressive():
    main_logger.info(f"Release parser for aggressive request")

    result = await parser_app.release_parser_for_aggressive()

    if result in ErrorMessages.ALL:
        return JSONResponse(status_code=500, content={"message": result})

    return JSONResponse(status_code=200, content={"message": "Browser has been released"})


@app.get('/number_of_browsers')
async def get_number_of_browsers():
    main_logger.info(f"Get number of browsers request")

    return parser_app.number_of_static_profiles + parser_app.number_of_dynamic_profiles


async def main():
    main_logger.info(f"Starting ParserApp")

    config = json.loads(open("config.json").read())

    static_proxies_list = config["static_proxies_list"]
    random.shuffle(static_proxies_list)

    number_of_static_profiles = config["number_of_static_profiles"]
    dynamic_proxies_list = config["dynamic_proxies_list"]
    number_of_dynamic_profiles = config["number_of_dynamic_profiles"]

    await parser_app.start(
        number_of_static_profiles=number_of_static_profiles,
        number_of_dynamic_profiles=number_of_dynamic_profiles,
        static_proxies_list=static_proxies_list,
        dynamic_proxies_list=dynamic_proxies_list
    )


if __name__ == '__main__':
    asyncio.run(
        main()
    )

    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000)

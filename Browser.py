import asyncio
import base64
import itertools
import json
import random
import re

import time
import traceback
from io import BytesIO

import requests
from PIL import Image

from ADS import ADS

from bs4 import BeautifulSoup

import pyppeteer

from ParseRequests import ParseRequests
from Statuses import BrowserStatuses, ErrorMessages


from logger import parser_exceptions_logger


class Browser:
    def __init__(self, profile_id):
        self.profile_id = profile_id
        self.status = BrowserStatuses.FREE

        self.pyppeteer_link = None
        self.driver = None
        self.page = None

    async def start(self):
        pyppeteer_link, driver_path = ADS.start_browser(self.profile_id)
        await asyncio.sleep(3)

        self.pyppeteer_link = pyppeteer_link

    async def check_page_available(self):
        info = list()

        try:
            info = await self.page.querySelectorAll('.spuBase_detail')
        except Exception:
            pass

        return len(info) > 0

    async def check_captcha(self):
        captcha = await self.page.querySelectorAll('#clickImg')
        return len(captcha) > 0

    async def parse_product_page_full(self, url, only_prices=False):
        try:
            self.driver = await pyppeteer.connect(browserWSEndpoint=self.pyppeteer_link, defaultViewport=None)

            if not self.page:
                self.page = await self.driver.newPage()

            # try:
            start_time = time.time()

            await self.page.goto(url, timeout=0)

            if await self.make_page_available() == ErrorMessages.ERROR:
                return ErrorMessages.ERROR

            res = {}

            if not only_prices:
                html_content = await self.page.content()
                res['size_table'] = await self.parse_size_tables(html_content)
                res['size_table']["key_orders"] = {}
                for table_name in res['size_table']:
                    res['size_table']["key_orders"][table_name] = list(res['size_table'][table_name].keys())

                res['params'] = await self.parse_params_table(html_content)
                res['descriptions'] = await self.parse_descriptions(html_content)

            res['prices'] = await self.parse_price_table()

            if res['prices'] == ErrorMessages.ERROR:
                return ErrorMessages.ERROR

            res['parse_time'] = str(round(time.time() - start_time, 2))
        except Exception as e:
            print(e)
            traceback.print_exc()
            parser_exceptions_logger.info(f"Exception {e} on parsing")
            return ErrorMessages.ERROR

        return res

    # except Exception as e:
    #     self.busy = False
    #     print("Exception while parsing page")
    #     print(e)
    #     return -1

    async def login_popup(self):
        popup = await self.page.querySelectorAll('.duLogin')
        return len(popup) > 0

    async def captcha_solution_checked(self):
        for i in range(4):
            try:
                marks = await self.page.querySelectorAll('#nToken1')
                # print("Marks", len(marks))

                if len(marks) == 0:
                    # print("No marks")
                    return

                await asyncio.sleep(1.5)
            except Exception:
                return

        return False


    async def make_page_available(self):
        cnt = 3

        while True:
            is_available = False
            captcha_on_a_page = False
            login_popup = False

            for i in range(40):
                if await self.check_page_available():
                    is_available = True
                    break

                if await self.check_captcha():
                    captcha_on_a_page = True
                    break

                if await self.login_popup():
                    login_popup = True
                    break

                await asyncio.sleep(0.2)

            if login_popup:
                print("Login popup, recreating")
                return ErrorMessages.ERROR

            if is_available:
                break

            if captcha_on_a_page:
                await self.solve_captcha(await self.page.content())
                result = await self.captcha_solution_checked()

                if result:
                    continue

                # await asyncio.sleep(10)

                # continue

            print("Reloading")
            await self.page.reload()
            cnt -= 1

            if cnt == 0:
                return ErrorMessages.ERROR

        return 0

    async def parse_descriptions(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        descriptions = soup.select('.imageAndText-content_info')

        if not descriptions:
            print("Product has no description")
            return []

        return [description.get_text() for description in descriptions]

    async def parse_price_table(self):
        await self.page.click('.payButton-content')

        popup = None

        cnt = 0
        while not popup:
            cnt += 1

            if cnt > 50:
                return ErrorMessages.ERROR

            if await self.login_popup():
                print("Login popup 2, close")
                return ErrorMessages.ERROR

            popup = await self.page.querySelector('.popup.show')
            await asyncio.sleep(0.2)

        await self.page.waitForSelector('.popup.show .close')
        close_notification_button = await popup.querySelector('.close')

        await close_notification_button.click()
        await asyncio.sleep(2)

        select_popup = None
        header_info = None
        select_container = None

        cnt = 0
        while not select_popup or not header_info or not select_container:
            cnt += 1

            if cnt > 50:
                return ErrorMessages.ERROR

            await asyncio.sleep(0.2)

            if await self.login_popup():
                print("Login popup 3, close")
                return ErrorMessages.ERROR

            select_popup = await self.page.querySelector('.select-mask')
            header_info = await select_popup.querySelector('.cover-desc')
            select_container = await self.page.querySelector('.select-container')

        return await self.non_recursive_parse_prices(select_popup, header_info, select_container)

    async def extract_item_wrap_text(self, item_wrap):
        text_element = await item_wrap.querySelector('.text')
        if text_element:
            return await self.page.evaluate('(element) => element.textContent', text_element)
        else:
            property_text_element = await item_wrap.querySelector('.property-text')
            if property_text_element:
                return await self.page.evaluate('(element) => element.textContent', property_text_element)
            else:
                return ""

    async def extract_item_wrap_texts(self, item_wraps):
        return await asyncio.gather(*[self.extract_item_wrap_text(item_wrap) for item_wrap in item_wraps])

    async def non_recursive_parse_prices(self, select_popup, header_info, select_container):
        res = {}

        select_container_html = await self.page.evaluate('(element) => element.innerHTML', select_container)
        soup = BeautifulSoup(select_container_html, 'html.parser')

        titles = [title.get_text() for title in soup.find_all(class_='title')]
        if not titles:
            titles = [""]

        list_wraps = await select_container.querySelectorAll('.list-wrap')

        item_wraps = []
        for list_wrap in list_wraps:
            item_wrap = await list_wrap.querySelectorAll('.item-wrap')
            item_wraps.append(item_wrap)

        item_wraps_texts = await asyncio.gather(*[self.extract_item_wrap_texts(row) for row in item_wraps])

        n = len(list_wraps)
        ranges = [range(len(list_wrap)) for list_wrap in item_wraps]

        last_comb = [-1 for _ in list_wraps]
        all_combinations = itertools.product(*ranges)

        res["configurations"] = {}

        for i in range(len(titles)):
            res["configurations"][titles[i]] = item_wraps_texts[i]

        res["units"] = []

        for combination in all_combinations:
            for i in range(n):
                if combination[i] != last_comb[i]:
                    await self.page.evaluate('(element) => element.scrollIntoView()', item_wraps[i][combination[i]])
                    await item_wraps[i][combination[i]].click()

            res2 = {}
            res2["buy_buttons"] = []
            res2["header"] = await self.page.evaluate('(element) => element.textContent', header_info)
            res2["current_url"] = self.page.url
            res2["current_configuration"] = {}

            for i in range(n):
                res2["current_configuration"][titles[i]] = item_wraps_texts[i][combination[i]]

            for buy_button in await select_popup.querySelectorAll('.button-view'):
                buy_button_info = {}

                buy_button_info['delivery_info'] = await self.page.evaluate(
                    '(element) => element.textContent', await buy_button.querySelector('.button-right'))
                buy_button_info['price'] = (await self.page.evaluate(
                    '(element) => element.textContent', await buy_button.querySelector('.price'))).replace(buy_button_info['delivery_info'], "")
                buy_button_info['additional_info'] = await self.page.evaluate(
                    '(element) => element.textContent', await buy_button.querySelector('.tradeTypeBox'))

                price_without_discount = await buy_button.querySelectorAll('.del-price')

                if price_without_discount:
                    buy_button_info['price_without_discount'] = await self.page.evaluate(
                        '(element) => element.textContent', price_without_discount[0])

                res2["buy_buttons"].append(buy_button_info)

            res["units"].append(res2)
            last_comb = combination

        return res

    async def solve_captcha(self, page_source):
        soup = BeautifulSoup(page_source, 'html.parser')
        img_tag1 = soup.find(id='clickImg')
        image = await self.page.querySelector("#clickImg")
        width, height = await asyncio.gather(
            self.page.evaluate('(element) => element.width', image),
            self.page.evaluate('(element) => element.height', image)
        )
        base64_blocks_image = img_tag1['src'].split(',')[1]
        img_tag2 = soup.find(id='clickTokenImg')
        base64_task_image = img_tag2['src'].split(',')[1]

        base64_data = base64_task_image
        image_data = base64.b64decode(base64_data)

        # Create a BytesIO object
        image_stream = BytesIO(image_data)

        # Open the image using PIL
        image = Image.open(image_stream)

        # Save the image locally
        image.save('local_image.png', 'PNG')

        data = {
            "blocks_image": base64_blocks_image,
            "task_image": base64_task_image,
            "size": [width, height]
        }

        headers = {
            "Content-Type": "application/json"
        }

        url = "https://sellout.su/captcha_images/solve_image_captcha"
        response = requests.post(url, json=data, headers=headers)
        result = response.json()['result']

        await self.click_captcha(result)

    @staticmethod
    def move_with_noise_deltas(start_x, start_y, end_x, end_y, num_steps, max_noise):
        # print(start_x, end_x)
        points_x = [start_x + i * ((end_x - start_x) // num_steps) for i in range(num_steps)]
        points_x.append(end_x)

        points_y = [start_y + i * ((end_y - start_y) // num_steps) for i in range(num_steps)]
        points_y.append(end_y)

        for i in range(1, num_steps):
            points_x[i] += random.randint(-max_noise, max_noise)
            points_y[i] += random.randint(-max_noise, max_noise)

        # print(start_x, end_x)
        # print(points_x)

        # print(start_y, end_y)
        # print(points_y)

        deltas = []
        for i in range(1, num_steps + 1):
            deltas.append((points_x[i] - points_x[i - 1], points_y[i] - points_y[i - 1]))

        # print(deltas)

        return deltas

    async def click_captcha(self, points):
        image = await self.page.querySelector("#clickImg")
        width, height = await asyncio.gather(
            self.page.evaluate('(element) => element.width', image),
            self.page.evaluate('(element) => element.height', image)
        )

        bounding_box = await image.boundingBox()
        x1 = bounding_box['x']
        y1 = bounding_box['y']

        mouse = self.page.mouse

        x, y = points[0]
        await mouse.click(x1 + x, y1 + y)

        cur_pos = {"x": x1 + x, "y": y1 + y}

        num_steps = 5
        max_noise = 2

        for point in points[1:]:
            # print("Iteration")
            deltas = self.move_with_noise_deltas(x, y, point[0], point[1], num_steps, max_noise)

            for delta in deltas[:3]:
                x1, y1 = cur_pos['x'], cur_pos['y']

                await mouse.move(x1 + delta[0], y1 + delta[1])
                cur_pos = {"x": x1 + delta[0], "y": y1 + delta[1]}
                await asyncio.sleep(random.randint(1, 2) * 0.01)

            for delta in deltas[3:]:
                x1, y1 = cur_pos['x'], cur_pos['y']

                await mouse.move(x1 + delta[0], y1 + delta[1])
                cur_pos = {"x": x1 + delta[0], "y": y1 + delta[1]}
                await asyncio.sleep(random.randint(1, 2) * 0.02)

            x1, y1 = cur_pos['x'], cur_pos['y']
            await mouse.move(x1 + deltas[-1][0] // 2, y1 + deltas[-1][1] // 2)
            cur_pos = {"x": x1 + deltas[-1][0] // 2, "y": y1 + deltas[-1][1] // 2}
            await asyncio.sleep(0.01)
            x1, y1 = cur_pos['x'], cur_pos['y']
            await mouse.click(x1 - deltas[-1][0] // 2, y1 - deltas[-1][1] // 2)
            cur_pos = {"x": x1 - deltas[-1][0] // 2, "y": y1 - deltas[-1][1] // 2}

            x, y = point[0], point[1]

    async def parse_params_table(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        res = {}

        params = soup.select('.baseProperty-content_info')

        for param in params:
            title = param.select_one('.content-title').get_text()
            value = param.select_one('.content-info').get_text()

            res[title] = value

        return res

    async def parse_size_tables(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        res = {}

        size_tables = soup.select('.size-report-view')

        if not size_tables:
            print("Product has no size table")
            return res

        for i, size_table in enumerate(size_tables):
            title_element = size_table.select_one('.size-title')

            if not title_element:
                title = str(i)
            else:
                title = title_element.get_text()

            res[title] = {}

            columns = size_table.select('.size-report-info')

            for column in columns:
                cells = column.select('.size-key')

                key = cells[0].get_text()
                res[title][key] = []

                for cell in cells[1:]:
                    res[title][key].append(cell.get_text())

        return res

import itertools
import json
import random
import re

import time
import requests

from ADS import ADS

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
from PIL import Image
import io
import base64


class Browser:
    def __init__(self, profile_id):
        self.profile_id = profile_id
        self.busy = False

        self.driver = None

    def start(self):
        selenium_link, driver_path = ADS.start_browser(self.profile_id)

        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", selenium_link)

        webdriver_service = Service(driver_path)
        self.driver = webdriver.Chrome(service=webdriver_service, options=chrome_options)

    def check_page_available(self):
        info = self.driver.find_elements(By.CLASS_NAME, 'spuBase_detail')

        return len(info) > 0

    def check_captcha(self):
        # captcha = self.driver.find_elements(By.ID, "rotateImg")
        captcha = self.driver.find_elements(By.ID, "clickImg")

        return len(captcha) > 0

    def parse_product_page_full(self, url, only_prices):
        try:
            self.busy = True

            start_time = time.time()
            self.driver.get(url)

            if self.make_page_available() == -1:
                return -1

            res = dict()

            if not only_prices:
                html_content = self.driver.page_source

                res['size_table'] = self.parse_size_tables(html_content)
                res['size_table']["key_orders"] = dict()
                for table_name in res['size_table']:
                    res['size_table']["key_orders"][table_name] = list(res['size_table'][table_name].keys())

                print(res['size_table']["key_orders"])
                res['params'] = self.parse_params_table(html_content)
                res['descriptions'] = self.parse_descriptions(html_content)

            res['prices'] = self.parse_price_table()
            res['parse_time'] = str(round(time.time() - start_time, 2))

            self.busy = False

            return json.dumps(res)
        except Exception as e:
            self.busy = False
            print("Exception while parsing page")
            print(e)
            return -1

    def make_page_available(self):
        cnt = 2

        while True:
            is_available = False
            captcha_on_a_page = False

            for i in range(20):
                if self.check_page_available():
                    is_available = True
                    break

                if self.check_captcha():
                    captcha_on_a_page = True
                    break

                time.sleep(0.2)

            if is_available:
                break

            if captcha_on_a_page:
                self.solve_captcha(self.driver.page_source)
                time.sleep(7)
                print("Reloading")
                self.driver.refresh()
                continue

            print("Reloading")
            self.driver.refresh()
            cnt -= 1

            if cnt == 0:
                return -1

        return 0

    def parse_descriptions(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')

        descriptions = soup.select('.imageAndText-content_info')

        if not descriptions:
            print("Product has no description")
            return []

        return [description.get_text() for description in descriptions]

    def parse_price_table(self):
        price_button = self.driver.find_elements(By.CLASS_NAME, 'payButton-content')

        if len(price_button) == 0:
            return
        price_button = price_button[0]

        price_button.click()

        # region Close popup
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "popup")))

        popup = self.driver.find_element(By.CLASS_NAME, "popup")

        close_notification_button = popup.find_element(By.CLASS_NAME, "close")
        self.driver.execute_script("arguments[0].click();", close_notification_button)
        # endregion

        time.sleep(0.3)
        select_popup = self.driver.find_element(By.CLASS_NAME, 'select-mask')
        header_info = select_popup.find_element(By.CLASS_NAME, 'cover-desc')

        select_container = self.driver.find_element(By.CLASS_NAME, 'select-container')

        return self.non_recursive_parse_prices(select_popup=select_popup, header_info=header_info,
                                               select_container=select_container)

    def non_recursive_parse_prices(self, select_popup, header_info, select_container):
        res = dict()

        select_container_html = select_container.get_attribute('innerHTML')
        soup = BeautifulSoup(select_container_html, 'html.parser')

        titles = [title.get_text() for title in soup.find_all(class_='title')]
        if not titles:
            titles = [""]

        list_wraps = select_container.find_elements(By.CLASS_NAME, 'list-wrap')
        item_wraps = [list_wrap.find_elements(By.CLASS_NAME, 'item-wrap') for list_wrap in list_wraps]

        item_wraps_texts = [
            [item_wrap for item_wrap in list_wrap.find_all(class_='item-wrap')] for
            list_wrap
            in soup.find_all(class_='list-wrap')]

        item_wraps_texts = [[item_wrap if item_wrap else "" for item_wrap in row] for row in
                            item_wraps_texts]

        for i in range(len(item_wraps_texts)):
            for j in range(len(item_wraps_texts[i])):
                item_wrap = item_wraps_texts[i][j]

                if item_wrap.find(class_='text'):
                    item_wraps_texts[i][j] = item_wrap.find(class_='text').get_text()
                elif item_wrap.find(class_='property-text'):
                    item_wraps_texts[i][j] = item_wrap.find(class_='property-text').get_text()
                else:
                    item_wraps_texts[i][j] = ""

        n = len(list_wraps)
        ranges = [range(len(list_wrap)) for list_wrap in item_wraps]

        last_comb = [-1 for _ in list_wraps]
        all_combinations = itertools.product(*ranges)

        res["configurations"] = dict()

        for i in range(len(titles)):
            res["configurations"][titles[i]] = item_wraps_texts[i]

        res["units"] = list()

        for combination in all_combinations:
            for i in range(n):
                if combination[i] != last_comb[i]:
                    self.driver.execute_script("arguments[0].scrollIntoView();", item_wraps[i][combination[i]])
                    item_wraps[i][combination[i]].click()

            res2 = dict()
            res2["buy_buttons"] = list()
            res2["header"] = header_info.get_attribute('textContent')
            res2["current_url"] = self.driver.current_url
            res2["current_configuration"] = dict()

            for i in range(n):
                res2["current_configuration"][titles[i]] = item_wraps_texts[i][combination[i]]

            for buy_button in select_popup.find_elements(By.CLASS_NAME, 'button-view'):
                buy_button_info = dict()

                buy_button_info['delivery_info'] = buy_button.find_element(
                    By.CLASS_NAME, 'button-right').get_attribute('textContent')
                buy_button_info['price'] = buy_button.find_element(
                    By.CLASS_NAME, 'price').get_attribute('textContent').replace(
                    buy_button_info['delivery_info'], "")
                buy_button_info['additional_info'] = buy_button.find_element(
                    By.CLASS_NAME, 'tradeTypeBox').get_attribute('textContent')

                price_without_discount = buy_button.find_elements(By.CLASS_NAME, 'del-price')

                if len(price_without_discount) != 0:
                    buy_button_info['price_without_discount'] = price_without_discount[0].get_attribute(
                        'textContent')

                res2["buy_buttons"].append(buy_button_info)

            res["units"].append(res2)
            last_comb = combination

        return res

    def recursive_parse_prices(self, select_popup, header_info, select_container, k=0):
        res = dict()

        titles = select_container.find_elements(By.CLASS_NAME, 'title')
        list_wraps = select_container.find_elements(By.CLASS_NAME, 'list-wrap')

        title = ""
        if titles:
            title = titles[k].get_attribute('textContent')
        res[title] = dict()

        for i, item_wrap in enumerate(list_wraps[k].find_elements(By.CLASS_NAME, 'item-wrap')):
            self.driver.execute_script("arguments[0].scrollIntoView();", item_wrap)
            item_wrap.click()

            # region item_wrap_text (Text on button)
            item_wrap_text = str(i)

            for possible_item_wrap_text_class in ['text', 'property-text']:
                item_wrap_text_elements = item_wrap.find_elements(By.CLASS_NAME, possible_item_wrap_text_class)

                if item_wrap_text_elements:
                    item_wrap_text = item_wrap_text_elements[0].get_attribute('textContent')
                    break
            # endregion

            res[title][item_wrap_text] = list()

            if len(list_wraps) - k == 1:
                for buy_button in select_popup.find_elements(By.CLASS_NAME, 'button-view'):
                    buy_button_info = dict()

                    buy_button_info['header'] = header_info.get_attribute('textContent')
                    buy_button_info['delivery_info'] = buy_button.find_element(
                        By.CLASS_NAME, 'button-right').get_attribute('textContent')
                    buy_button_info['price'] = buy_button.find_element(
                        By.CLASS_NAME, 'price').get_attribute('textContent').replace(
                        buy_button_info['delivery_info'], "")
                    buy_button_info['additional_info'] = buy_button.find_element(
                        By.CLASS_NAME, 'tradeTypeBox').get_attribute('textContent')
                    buy_button_info['current_url'] = self.driver.current_url

                    price_without_discount = buy_button.find_elements(By.CLASS_NAME, 'del-price')

                    if len(price_without_discount) != 0:
                        buy_button_info['price_without_discount'] = price_without_discount[0].get_attribute(
                            'textContent')

                    res[title][item_wrap_text].append(buy_button_info)
            else:
                res[title][item_wrap_text] = self.recursive_parse_prices(
                    select_popup=select_popup, header_info=header_info,
                    select_container=select_container)

        return res

    def parse_params_table(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        res = {}

        params = soup.select('.baseProperty-content_info')

        for param in params:
            title = param.select_one('.content-title').get_text()
            value = param.select_one('.content-info').get_text()

            res[title] = value

        return res

    def parse_size_tables(self, html_content):
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

    def solve_captcha(self, page_source):
        soup = BeautifulSoup(page_source, 'html.parser')

        # img_tag1 = soup.find(id='rotateBlock')
        # base64_data1 = img_tag1['src'].split(',')[1]
        #
        # img_tag2 = soup.find(id='rotateImg')
        # base64_data2 = img_tag2['src'].split(',')[1]
        #
        # image_data1 = base64.b64decode(base64_data1)
        # image1 = Image.open(io.BytesIO(image_data1))
        #
        # image_data2 = base64.b64decode(base64_data2)
        # image2 = Image.open(io.BytesIO(image_data2))
        #
        # image1.save('captcha_image1.png')
        # image2.save('captcha_image2.png')

        # url = 'http://51.250.74.115:5001/process_captcha'
        # with open('captcha_image1.png', 'rb') as img1, open('captcha_image2.png', 'rb') as img2:
        #     files = {
        #         'captcha_large': img1,
        #         'captcha_small': img2
        #     }
        #
        #     response = requests.post(url, files=files)
        # self.rotate_captcha(result)
        img_tag1 = soup.find(id='clickImg')
        image = self.driver.find_element(By.ID, "clickImg")

        width, height = image.size['width'], image.size['height']

        base64_blocks_image = img_tag1['src'].split(',')[1]

        img_tag2 = soup.find(id='clickTokenImg')
        base64_task_image = img_tag2['src'].split(',')[1]

        data = {
            "blocks_image": base64_blocks_image,
            "task_image": base64_task_image,
            "size": [width, height]
        }


        headers = {
            "Content-Type": "application/json"
        }

        url = "http://localhost:5001/solve_image_captcha"
        response = requests.post(url, json=data, headers=headers)

        result = response.json()['result']

        self.click_captcha(result)

    @staticmethod
    def move_with_noise_deltas(start_x, start_y, end_x, end_y, num_steps, max_noise):
        print(start_x, end_x)
        points_x = [start_x + i * ((end_x - start_x) // num_steps) for i in range(num_steps)]
        points_x.append(end_x)

        points_y = [start_y + i * ((end_y - start_y) // num_steps) for i in range(num_steps)]
        points_y.append(end_y)

        for i in range(1, num_steps):
            points_x[i] += random.randint(-max_noise, max_noise)
            points_y[i] += random.randint(-max_noise, max_noise)

        print(start_x, end_x)
        print(points_x)

        print(start_y, end_y)
        print(points_y)

        deltas = list()
        for i in range(1, num_steps + 1):
            deltas.append((points_x[i] - points_x[i - 1], points_y[i] - points_y[i - 1]))

        print(deltas)

        return deltas

    def click_captcha(self, points):
        image = self.driver.find_element(By.ID, "clickImg")
        width, height = image.size['width'], image.size['height']
        print(width, height)

        action_chains = ActionChains(self.driver)
        x, y = points[0]
        print(x, y)
        action_chains.move_to_element_with_offset(image, x - width // 2, y - height // 2).click().perform()

        num_steps = 5
        max_noise = 2

        for point in points[1:]:
            print("Iteration")
            deltas = self.move_with_noise_deltas(x, y, point[0], point[1], num_steps, max_noise)

            for delta in deltas[:3]:
                action_chains.move_by_offset(delta[0], delta[1])
                time.sleep(random.randint(1, 2) * 0.001)

            for delta in deltas[3:]:
                action_chains.move_by_offset(delta[0], delta[1])
                time.sleep(random.randint(1, 2) * 0.002)

            action_chains.move_by_offset(deltas[-1][0] // 2, deltas[-1][1] // 2)
            time.sleep(0.001)
            action_chains.move_by_offset(-deltas[-1][0] // 2, -deltas[-1][1] // 2)

            action_chains.click().perform()
            x, y = point[0], point[1]

    def rotate_captcha(self, result):
        element = self.driver.find_element("id", "slideHint")

        # Get the width of the element
        width = element.size['width']

        element = self.driver.find_element("id", "slideBtn")
        width = width - element.size['width']

        actions = ActionChains(self.driver)

        # Perform the desired actions on the element
        actions.click_and_hold(element)

        total = int(result * width / 360)

        # region V1
        # offset = random.randint(5, 15)
        #
        # for i in range(total // 3 + offset):
        #     actions.move_by_offset(3, 0)
        #
        #     if random.randint(1, 3) == 1:
        #         time.sleep(random.randint(1, 2) * 0.001)
        #
        # for i in range(total % 3):
        #     actions.move_by_offset(1, 0)
        #     time.sleep(random.randint(1, 2) * 0.001)
        #
        # for i in range(offset):
        #     actions.move_by_offset(-3, 0)
        #     time.sleep(random.randint(1, 2) * 0.001)
        # endregion
        # region V2
        points = list()
        points.append(0)
        sleep = list()

        for i in range(10):
            offset_y = random.choices(population=[0, 1, 2], weights=[10, 75, 15], k=1)[0]

            points.append(random.randint(total // 9 * i, total // 9 * i + total // 9))
            actions.move_by_offset(points[-1] - points[-2], offset_y)

            time.sleep(random.randint(0, 1) * 0.001)

        for i in range(5):
            offset_y = random.choices(population=[-1, 0, 1, 2], weights=[10, 10, 40, 40], k=1)[0]
            offset_x = random.randint(-3, -2)

            points.append(points[-1] + offset_x)
            actions.move_by_offset(points[-1] - points[-2], offset_y)

            time.sleep(random.randint(0, 1) * 0.002)

        temp = int(total > points[-1]) * 2 - 1
        for i in range(abs(points[-1] - total)):
            actions.move_by_offset(1 * temp, random.randint(-2, 2))
            time.sleep(random.randint(0, 1) * 0.001)
        # endregion

        actions.release().perform()

    def element_has_text(self):
        element = self.driver.find_element(By.CLASS_NAME, 'your-element-class')
        if element.get_attribute('textContent'):
            return element
        else:
            return False

    def update_proxy(self, proxy):
        self.busy = True

        ADS.update_profile_proxy(profile_id=self.profile_id, proxy=proxy)
        ADS.stop_browser(self.profile_id)
        self.start()

        self.busy = False

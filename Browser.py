import json
import random

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
        time.sleep(2)
        info = self.driver.find_elements(By.CLASS_NAME, 'spuBase_detail')

        return len(info) > 0

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
        cnt = 5
        while True:
            if self.check_page_available():
                break

            try:
                WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.ID, "rotateImg"))
                )
            except:
                cnt -= 1

                if cnt == 0:
                    return -1

                print("Reloading")
                self.driver.refresh()
                continue

            self.solve_captcha(self.driver.page_source)
            time.sleep(5)

            if not self.check_page_available():
                print("Reloading")
                self.driver.refresh()
                time.sleep(5)
            else:
                print("Captcha has been passed successfully")
                break

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

        return self.recursive_parse_prices(select_popup=select_popup, header_info=header_info,
                                           select_container=select_container)

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
                    select_container=select_container, k=k + 1)

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

        img_tag1 = soup.find(id='rotateBlock')
        base64_data1 = img_tag1['src'].split(',')[1]

        img_tag2 = soup.find(id='rotateImg')
        base64_data2 = img_tag2['src'].split(',')[1]

        image_data1 = base64.b64decode(base64_data1)
        image1 = Image.open(io.BytesIO(image_data1))

        image_data2 = base64.b64decode(base64_data2)
        image2 = Image.open(io.BytesIO(image_data2))

        image1.save('captcha_image1.png')
        image2.save('captcha_image2.png')

        url = 'http://51.250.74.115:5001/process_captcha'
        with open('captcha_image1.png', 'rb') as img1, open('captcha_image2.png', 'rb') as img2:
            files = {
                'captcha_large': img1,
                'captcha_small': img2
            }

            response = requests.post(url, files=files)

        result = response.json()['result']

        self.rotate_captcha(result)

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

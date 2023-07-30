import builtins
import random
import threading
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

import queue


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
        time.sleep(1)
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
                res['size_table'] = self.parse_size_table()
                res['params'] = self.parse_params_table()
                res['description'] = self.parse_description()

            res['prices'] = self.parse_price_table()
            res['parse_time'] = str(round(time.time() - start_time, 2))

            self.busy = False

            return res
        except Exception as e:
            self.busy = False
            print("Exception while parsing page")
            print(e)
            return -1

    def make_page_available(self):
        cnt = 10
        while True:
            if self.check_page_available():
                break

            try:
                WebDriverWait(self.driver, 4).until(
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

    def parse_description(self):
        description = self.driver.find_elements(By.CLASS_NAME, 'imageAndText-content_info')

        if len(description) == 0:
            print("Product has no description")
            return ""

        description = description[0]
        return description.get_attribute('textContent')

    def parse_price_table(self):
        WebDriverWait(self.driver, 2).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'payButton-content')))
        WebDriverWait(self.driver, 2).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'payButton-content')))

        price_button = self.driver.find_element(By.CLASS_NAME, 'payButton-content')
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

    def parse_params_table(self):
        res = dict()

        params = self.driver.find_elements(By.CLASS_NAME, "baseProperty-content_info")

        for param in params:
            title = param.find_element(By.CLASS_NAME, "content-title").get_attribute('textContent')
            value = param.find_element(By.CLASS_NAME, "content-info").get_attribute('textContent')

            res[title] = value

        return res

    def parse_size_table(self):
        size_tables = self.driver.find_elements(By.CLASS_NAME, "size-report-view")

        if len(size_tables) == 0:
            print("Product has no size table")
            return dict()

        res = dict()

        for i, size_table in enumerate(size_tables):
            title = size_table.find_elements(By.CLASS_NAME, "size-title")

            if len(title) == 0:
                title = str(i)
            else:
                title = title[0].get_attribute('textContent')

            res[title] = dict()

            columns = size_table.find_elements(By.CLASS_NAME, "size-report-info")

            for column in columns:
                cells = column.find_elements(By.CLASS_NAME, "size-key")

                key = cells[0].get_attribute('textContent')
                res[title][key] = list()

                for cell in cells[1:]:
                    res[title][key].append(cell.get_attribute('textContent'))

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


class ParserApp:
    def __init__(self):
        self.browsers = list()
        self.get_proxy_url = ""
        self.proxy_list = list()

    def update_proxies(self):
        while True:
            time_to_wait = 120

            response = requests.request("GET", self.get_proxy_url).text

            for proxy in list(map(lambda proxy_host_port: "http:" + proxy_host_port, response.split())):
                self.proxy_list.append(proxy)

            print(self.proxy_list)

            for i, browser in enumerate(self.browsers):
                while browser.busy:
                    print(f"Waiting while browser {i} busy")
                    time.sleep(5)
                    time_to_wait -= 5

                print(f"Updating browser {i} proxy")
                browser.update_proxy(self.proxy_list.pop())

            time_to_wait = max(time_to_wait, 1)
            time.sleep(time_to_wait)

    def start(self, get_proxy_url, number_of_profiles=1):
        self.get_proxy_url = get_proxy_url

        ADS.clear_all_profiles()

        for _ in range(number_of_profiles):
            ADS.create_profile()

        profile_ids = list(map(lambda profile: profile['user_id'], ADS.list_all_profiles()))

        for profile_id in profile_ids:
            self.browsers.append(Browser(profile_id))

        # for browser in self.browsers:
        #     browser.start()

        threading.Thread(target=self.update_proxies).start()

    def recreate_browser(self, browser_index):
        ADS.stop_browser(self.browsers[browser_index].profile_id)
        ADS.delete_profile(self.browsers[browser_index].profile_id)

        if len(self.proxy_list) != 0:
            ADS.create_profile(proxy=self.proxy_list.pop())
        else:
            ADS.create_profile()

        self.browsers[browser_index] = Browser(ADS.list_all_profiles()[0]['user_id'])
        self.browsers[browser_index].start()

    def parse_product_page_full(self, url, only_prices):
        for i in range(len(self.browsers)):
            if not self.browsers[i].busy:
                res = self.browsers[i].parse_product_page_full(url, only_prices)

                while res == -1:
                    print(f"Recreating browser {i}")
                    self.recreate_browser(i)
                    res = self.browsers[i].parse_product_page_full(url, only_prices)

                return res

        return -1

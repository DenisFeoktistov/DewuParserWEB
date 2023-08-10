import datetime
import time
import requests

from ADS import ADS
from Browser import Browser


class ParserApp:
    def __init__(self):
        self.static_proxies_browsers = list()
        self.dynamic_proxies_browsers = list()

        self.static_proxies_list = list()
        self.dynamic_proxies_list = list()

    def start(self, number_of_static_profiles=0, number_of_dynamic_profiles=0, dynamic_proxies_list=tuple(),
              static_proxies_list=tuple()):

        self.static_proxies_list = list(static_proxies_list)
        self.dynamic_proxies_list = list(dynamic_proxies_list)

        ADS.clear_all_profiles()

        for i in range(number_of_static_profiles):
            profile_id = ADS.create_profile(proxy=self.static_proxies_list[i])['data']['id']
            self.static_proxies_browsers.append(Browser(profile_id))

            self.static_proxies_list.append(self.static_proxies_list.pop(0))

        for i in range(number_of_dynamic_profiles):
            profile_id = ADS.create_profile(proxy=self.dynamic_proxies_list[i])['data']['id']
            self.dynamic_proxies_browsers.append(Browser(profile_id))

        print("Starting browsers with static proxies")
        for browser in self.static_proxies_browsers:
            browser.start()

        print("Starting browsers with dynamic proxies")
        for browser in self.dynamic_proxies_browsers:
            browser.start()

    def recreate_browser(self, i):
        if i < len(self.static_proxies_browsers):
            with open("logs.txt", "a") as logs_file:
                logs_file.write(
                    f"Recreating browser {i} with static proxy {self.static_proxies_list[0]} Current time is {datetime.datetime.now()}\n")

            ADS.stop_browser(self.static_proxies_browsers[i].profile_id)
            ADS.delete_profile(self.static_proxies_browsers[i].profile_id)

            profile_id = ADS.create_profile(proxy=self.static_proxies_list[i])['data']['id']
            self.static_proxies_list.append(self.static_proxies_list.pop(0))

            self.static_proxies_browsers[i] = Browser(profile_id)
            self.static_proxies_browsers[i].start()
        else:
            i = i - len(self.static_proxies_browsers)

            with open("logs.txt", "a") as logs_file:
                logs_file.write(
                    f"Recreating browser {i} with dynamic proxy {self.dynamic_proxies_list[0]} Current time is {datetime.datetime.now()}\n")

            ADS.stop_browser(self.dynamic_proxies_browsers[i].profile_id)
            ADS.delete_profile(self.dynamic_proxies_browsers[i].profile_id)

            profile_id = ADS.create_profile(proxy=self.dynamic_proxies_list[i])['data']['id']

            self.dynamic_proxies_browsers[i] = Browser(profile_id)
            self.dynamic_proxies_browsers[i].start()

    def parse_product_page_full_temp(self, url, only_prices, i):
        browser = (
            self.static_proxies_browsers[i] if i < len(self.static_proxies_browsers) else self.dynamic_proxies_browsers[
                i - len(self.static_proxies_browsers)])

        res = browser.parse_product_page_full(url, only_prices)

        while res == -1:
            print(f"Recreating browser {i}")
            self.recreate_browser(i)

            browser = (
                self.static_proxies_browsers[i] if i < len(self.static_proxies_browsers) else
                self.dynamic_proxies_browsers[
                    i - len(self.static_proxies_browsers)])
            res = browser.parse_product_page_full(url, only_prices)

        return res

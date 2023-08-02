import time
import requests

from ADS import ADS
from Browser import Browser


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

    def start(self, number_of_profiles=1, proxy_list=tuple()):
        # self.get_proxy_url = get_proxy_url

        ADS.clear_all_profiles()

        for i in range(number_of_profiles):
            if len(proxy_list) >= number_of_profiles:
                ADS.create_profile(proxy_list[i])
            else:
                ADS.create_profile()

        profile_ids = list(map(lambda profile: profile['user_id'], ADS.list_all_profiles()))

        for profile_id in profile_ids:
            self.browsers.append(Browser(profile_id))

        for browser in self.browsers:
            browser.start()

        # threading.Thread(target=self.update_proxies).start()

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

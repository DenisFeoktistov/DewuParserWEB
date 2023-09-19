import asyncio
import datetime

from ADS import ADS
from Browser import Browser
from ParseRequests import ParseRequests
from Statuses import BrowserStatuses, ErrorMessages


from logger import parser_exceptions_logger, main_logger


class ParserApp:
    def __init__(self):
        self.static_proxies_browsers = list()
        self.static_proxies_browsers_tasks = list()
        self.dynamic_proxies_browsers = list()
        self.dynamic_proxies_browsers_tasks = list()

        self.static_proxies_list = list()
        self.dynamic_proxies_list = list()

        self.number_of_static_profiles = None
        self.number_of_dynamic_profiles = None

        # asyncio = loop

    async def start(self, number_of_static_profiles=0, number_of_dynamic_profiles=0, dynamic_proxies_list=tuple(),
                    static_proxies_list=tuple()):
        self.number_of_static_profiles = number_of_static_profiles
        self.number_of_dynamic_profiles = number_of_dynamic_profiles

        self.static_proxies_list = list(static_proxies_list)
        self.dynamic_proxies_list = list(dynamic_proxies_list)

        ADS.clear_all_profiles()

        for i in range(number_of_static_profiles):
            profile_id = ADS.create_profile(proxy=self.static_proxies_list[0])['data']['id']
            self.static_proxies_browsers.append(Browser(profile_id))
            self.static_proxies_browsers_tasks.append(None)

            self.static_proxies_list.append(self.static_proxies_list.pop(0))

        for i in range(number_of_dynamic_profiles):
            profile_id = ADS.create_profile(proxy=self.dynamic_proxies_list[i])['data']['id']
            self.dynamic_proxies_browsers.append(Browser(profile_id))
            self.dynamic_proxies_browsers_tasks.append(None)

        print("Starting browsers with static proxies")
        for browser in self.static_proxies_browsers:
            await browser.start()

        print("Starting browsers with dynamic proxies")
        for browser in self.dynamic_proxies_browsers:
            await browser.start()

    async def recreate_browser(self, i):
        if i < len(self.static_proxies_browsers):
            with open("logs.txt", "a") as logs_file:
                logs_file.write(
                    f"Recreating browser {i} with static proxy {self.static_proxies_list[0]} Current time is {datetime.datetime.now()}\n")

            ADS.stop_browser(self.static_proxies_browsers[i].profile_id)
            ADS.delete_profile(self.static_proxies_browsers[i].profile_id)

            profile_id = ADS.create_profile(proxy=self.static_proxies_list[0])['data']['id']
            self.static_proxies_list.append(self.static_proxies_list.pop(0))

            self.static_proxies_browsers[i] = Browser(profile_id)
            await self.static_proxies_browsers[i].start()
        else:
            i = i - len(self.static_proxies_browsers)

            with open("logs.txt", "a") as logs_file:
                logs_file.write(
                    f"Recreating browser {i} with dynamic proxy {self.dynamic_proxies_list[i]} Current time is {datetime.datetime.now()}\n")

            ADS.stop_browser(self.dynamic_proxies_browsers[i].profile_id)
            ADS.delete_profile(self.dynamic_proxies_browsers[i].profile_id)

            profile_id = ADS.create_profile(proxy=self.dynamic_proxies_list[i])['data']['id']

            self.dynamic_proxies_browsers[i] = Browser(profile_id)
            await self.dynamic_proxies_browsers[i].start()

    async def process_url(self, browser_index, url, parse_request):
        browser = (self.static_proxies_browsers[browser_index] if browser_index < len(self.static_proxies_browsers) else
                   self.dynamic_proxies_browsers[browser_index - len(self.static_proxies_browsers)])

        if parse_request == ParseRequests.MAIN:
            browser.status = BrowserStatuses.MAIN_IN_WORK

        if parse_request == ParseRequests.PASSIVE:
            browser.status = BrowserStatuses.PASSIVE_IN_WORK

        if parse_request == ParseRequests.AGGRESSIVE:
            browser.status = BrowserStatuses.AGGRESSIVE_IN_WORK

        print(id(asyncio.get_event_loop()))
        result = await browser.parse_product_page_full(url)

        cnt = 1
        while result == ErrorMessages.ERROR and cnt < 3:
            await self.recreate_browser(browser_index)

            result = await browser.parse_product_page_full(url)
            cnt += 1

        if parse_request == ParseRequests.MAIN:
            browser.status = BrowserStatuses.FREE

        if parse_request == ParseRequests.PASSIVE:
            browser.status = BrowserStatuses.FREE

        if parse_request == ParseRequests.AGGRESSIVE:
            browser.status = BrowserStatuses.AGGRESSIVE_RESERVED

        return result

    async def parse_product_page(self, url, parse_request):
        browser = None
        browser_index = None

        if parse_request == ParseRequests.MAIN:
            for i, browser1 in enumerate(self.static_proxies_browsers):
                if not browser and browser1.status in (BrowserStatuses.FREE, BrowserStatuses.PASSIVE_IN_WORK):
                    browser = browser1
                    browser_index = i

            for i, browser1 in enumerate(self.dynamic_proxies_browsers):
                if not browser and browser1.status in (BrowserStatuses.FREE, BrowserStatuses.PASSIVE_IN_WORK):
                    browser = browser1
                    browser_index = i + len(self.static_proxies_browsers)

        if parse_request == ParseRequests.PASSIVE:
            for browser1 in self.static_proxies_browsers:
                if not browser and browser1.status == BrowserStatuses.FREE:
                    browser = browser1

            for browser1 in self.dynamic_proxies_browsers:
                if not browser and browser1.status == BrowserStatuses.FREE:
                    browser = browser1

        if parse_request == ParseRequests.AGGRESSIVE:
            for browser1 in self.static_proxies_browsers:
                if not browser and browser1.status == BrowserStatuses.AGGRESSIVE_RESERVED:
                    browser = browser1

            for browser1 in self.dynamic_proxies_browsers:
                if not browser and browser1.status == BrowserStatuses.AGGRESSIVE_RESERVED:
                    browser = browser1

        if not browser:
            return ErrorMessages.ALL_BROWSERS_ARE_BUSY

        print(asyncio.get_event_loop())

        task = asyncio.create_task(self.process_url(browser_index, url, parse_request))
        if browser_index < len(self.static_proxies_browsers):
            self.static_proxies_browsers_tasks[browser_index] = task
        else:
            self.dynamic_proxies_browsers_tasks[browser_index - len(self.static_proxies_browsers)] = task

        try:
            result = await asyncio.gather(task)
        except asyncio.CancelledError as e:
            return ErrorMessages.INTERRUPTED

        return result

    async def reserve_parser_for_aggressive(self):
        browser = None

        for browser1 in self.static_proxies_browsers:
            if not browser and browser1.status in (BrowserStatuses.FREE, BrowserStatuses.PASSIVE_IN_WORK):
                browser = browser1
                browser1.status = BrowserStatuses.AGGRESSIVE_RESERVED

        for browser1 in self.dynamic_proxies_browsers:
            if not browser and browser1.status in (BrowserStatuses.FREE, BrowserStatuses.PASSIVE_IN_WORK):
                browser = browser1
                browser1.status = BrowserStatuses.AGGRESSIVE_RESERVED

        if browser:
            return 0
        else:
            return ErrorMessages.ALL_BROWSERS_ARE_BUSY

    async def release_parser_for_aggressive(self):
        browser = None

        for browser1 in self.static_proxies_browsers:
            if not browser and browser1.status == BrowserStatuses.AGGRESSIVE_RESERVED:
                browser = browser1
                browser1.status = BrowserStatuses.FREE

        for browser1 in self.dynamic_proxies_browsers:
            if not browser and browser1.status == BrowserStatuses.AGGRESSIVE_RESERVED:
                browser = browser1
                browser1.status = BrowserStatuses.FREE

        if browser:
            return 0
        else:
            return ErrorMessages.ALL_BROWSERS_ARE_BUSY

        # res = asyncio.run(browser.parse_product_page_full(url, only_prices))
        # cnt = 0
        #
        # while res == -1:
        #     cnt += 1
        #
        #     if cnt == 2:
        #         return -1
        #     print(f"Recreating browser {i}")
        #     with ADS_LOCK:
        #         await self.recreate_browser(i)
        #         print(datetime.datetime.now())
        #         time.sleep(3)
        #
        #     browser = (
        #         self.static_proxies_browsers[i] if i < len(self.static_proxies_browsers) else
        #         self.dynamic_proxies_browsers[
        #             i - len(self.static_proxies_browsers)])
        #     res = asyncio.run(browser.parse_product_page_full(url, only_prices))
        #
        # return res

import asyncio
import datetime
import random

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

    async def recreate_browser(self, i, status=None):
        if i < len(self.static_proxies_browsers):
            ADS.stop_browser(self.static_proxies_browsers[i].profile_id)
            ADS.delete_profile(self.static_proxies_browsers[i].profile_id)

            profile_id = ADS.create_profile(proxy=self.static_proxies_list[0])['data']['id']
            self.static_proxies_list.append(self.static_proxies_list.pop(0))

            self.static_proxies_browsers[i] = Browser(profile_id)

            if status:
                self.static_proxies_browsers[i].status = status

            await self.static_proxies_browsers[i].start()
        else:
            i = i - len(self.static_proxies_browsers)

            ADS.stop_browser(self.dynamic_proxies_browsers[i].profile_id)
            ADS.delete_profile(self.dynamic_proxies_browsers[i].profile_id)

            profile_id = ADS.create_profile(proxy=self.dynamic_proxies_list[i])['data']['id']

            self.dynamic_proxies_browsers[i] = Browser(profile_id)

            if status:
                self.dynamic_proxies_browsers[i].status = status

            await self.dynamic_proxies_browsers[i].start()

    async def process_url(self, browser_index, url, parse_request):
        browser = (self.static_proxies_browsers[browser_index] if browser_index < len(self.static_proxies_browsers) else
                   self.dynamic_proxies_browsers[browser_index - len(self.static_proxies_browsers)])
        status = browser.status

        result = await browser.parse_product_page_full(url)

        cnt = 1
        while result == ErrorMessages.ERROR and cnt <= 3:
            await self.recreate_browser(browser_index, status)
            browser = (
                self.static_proxies_browsers[browser_index] if browser_index < len(self.static_proxies_browsers) else
                self.dynamic_proxies_browsers[browser_index - len(self.static_proxies_browsers)])

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
        # browser = None
        # browser_index = None

        browsers = list()
        browser_status = None
        browser_indexes = list()

        if parse_request == ParseRequests.MAIN:
            browser_status = BrowserStatuses.MAIN_IN_WORK

            for i, browser1 in enumerate(self.static_proxies_browsers):
                if browser1.status in (BrowserStatuses.FREE, BrowserStatuses.PASSIVE_IN_WORK):
                    browsers.append(browser1)
                    browser_indexes.append(i)

            for i, browser1 in enumerate(self.dynamic_proxies_browsers):
                if browser1.status in (BrowserStatuses.FREE, BrowserStatuses.PASSIVE_IN_WORK):
                    browsers.append(browser1)
                    browser_indexes.append(i + len(self.static_proxies_browsers))

        if parse_request == ParseRequests.PASSIVE:
            browser_status = BrowserStatuses.PASSIVE_IN_WORK

            for i, browser1 in enumerate(self.static_proxies_browsers):
                if browser1.status == BrowserStatuses.FREE:
                    browsers.append(browser1)
                    browser_indexes.append(i)

            for i, browser1 in enumerate(self.dynamic_proxies_browsers):
                if browser1.status == BrowserStatuses.FREE:
                    browsers.append(browser1)
                    browser_indexes.append(i + len(self.static_proxies_browsers))

        if parse_request == ParseRequests.AGGRESSIVE:
            browser_status = BrowserStatuses.AGGRESSIVE_IN_WORK

            for i, browser1 in enumerate(self.static_proxies_browsers):
                if browser1.status == BrowserStatuses.AGGRESSIVE_RESERVED:
                    browsers.append(browser1)
                    browser_indexes.append(i)

            for i, browser1 in enumerate(self.dynamic_proxies_browsers):
                if browser1.status == BrowserStatuses.AGGRESSIVE_RESERVED:
                    browsers.append(browser1)
                    browser_indexes.append(i + len(self.static_proxies_browsers))

        if len(browsers) == 0:
            return ErrorMessages.ALL_BROWSERS_ARE_BUSY

        i = random.randint(0, len(browsers) - 1)

        browser_index = browser_indexes[i]
        browser = browsers[i]
        browser.status = browser_status

        # print(*map(lambda b: b.status, self.static_proxies_browsers),
        #       *map(lambda b: b.status, self.dynamic_proxies_browsers))

        task = asyncio.create_task(self.process_url(browser_index, url, parse_request))
        if browser_index < len(self.static_proxies_browsers):
            if self.static_proxies_browsers_tasks[browser_index]:
                self.static_proxies_browsers_tasks[browser_index].cancel()

            self.static_proxies_browsers_tasks[browser_index] = task
        else:
            if self.dynamic_proxies_browsers_tasks[browser_index - len(self.static_proxies_browsers)]:
                self.dynamic_proxies_browsers_tasks[browser_index - len(self.static_proxies_browsers)].cancel()

            self.dynamic_proxies_browsers_tasks[browser_index - len(self.static_proxies_browsers)] = task

        try:
            result = (await asyncio.gather(task))[0]
        except asyncio.CancelledError as e:
            print(e)
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

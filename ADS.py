import random
import time
from time import sleep

import requests


class ADS:
    DEBUG = True

    STATUS_URL = "http://localhost:50325/status"
    API_URL = "http://localhost:50325/api/v1/"

    ERR_TOO_MANY_REQUESTS = "Too many request per second, please check"

    FINGERPRINT_CONFIG = {
        "fingerprint_config": {
            "automatic_timezone": "1",
            "language_switch": "1",
            "language": ["zh-CN", "zh"],
            "scan_port_type": "1",
            # "screen_resolution": "300_1400",
            "country": "cn",
            "webgl": "3",
            "webrtc": "proxy",
            "audio": "0",
            "media_devices": "0",
            # "random_ua": {"ua_system_version": ["Android 9", "Android 10", "Android 11", "Android 12", "Android 13"]}
        }
    }

    NO_PROXY_CONFIG = {
        "user_proxy_config": {"proxy_soft": "no_proxy"}
    }

    LAST_REQUEST_TIME = time.time()
    JSON_HEADERS = {'Content-Type': 'application/json'}

    MAIN_GROUP_NAME = "DEWU"

    @staticmethod
    def generate_fingerprint_config():
        res = ADS.FINGERPRINT_CONFIG
        width = random.randint(47, 53) * 10
        height = random.randint(85, 95) * 10
        res['fingerprint_config']['screen_resolution'] = str(width) + "_" + str(height)

        return res

    def __init__(self):
        pass

    @staticmethod
    def wait_until_available():
        while time.time() - ADS.LAST_REQUEST_TIME < 1.2:
            time.sleep(0.1)

        ADS.LAST_REQUEST_TIME = time.time()

    @staticmethod
    def check_status_okay():
        url = ADS.STATUS_URL
        request_done = False

        while not request_done:
            try:
                ADS.wait_until_available()
                response = requests.request("GET", url)

                if response.json()['code'] == 0:
                    return True

            except requests.exceptions.ConnectionError:
                print("ADS connection error, trying again in 1 second")

            sleep(1)

    @staticmethod
    def list_all_profiles():
        url = ADS.API_URL + "user/list?page_size=100"

        ADS.wait_until_available()
        response = requests.request("GET", url)

        if ADS.DEBUG:
            print("List all profiles response: ", response.text)

        if response.json():
            return response.json()['data']['list']
        else:
            return list()

    @staticmethod
    def list_all_groups():
        url = ADS.API_URL + "group/list"

        ADS.wait_until_available()
        response = requests.request("GET", url)

        if ADS.DEBUG:
            print("List all groups response: ", response.text)

        if response.json():
            return response.json()['data']['list']
        else:
            return list()

    @staticmethod
    def create_group(name):
        url = ADS.API_URL + "group/create"

        body = {
            "group_name": name
        }

        ADS.wait_until_available()
        response = requests.request("POST", url, json=body, headers=ADS.JSON_HEADERS)

        if ADS.DEBUG:
            print(f"Create group {name} response: ", response.text)

    @staticmethod
    def create_profile(proxy=""):
        groups = ADS.list_all_groups()
        group_id = ""

        for group in groups:
            if group['group_name'] == ADS.MAIN_GROUP_NAME:
                group_id = group['group_id']

        if not group_id:
            ADS.create_group(ADS.MAIN_GROUP_NAME)

            for group in groups:
                if group['group_name'] == ADS.MAIN_GROUP_NAME:
                    group_id = group['group_id']

        url = ADS.API_URL + "user/create"

        proxy_config = ADS.NO_PROXY_CONFIG

        if proxy:
            proxy_split = proxy.split(":")

            if len(proxy_split) == 5:
                proxy_config = {
                    "user_proxy_config": {
                        "proxy_type": proxy_split[0],
                        "proxy_host": proxy_split[1],
                        "proxy_port": proxy_split[2],
                        "proxy_user": proxy_split[3],
                        "proxy_password": proxy_split[4],
                        "proxy_soft": "other"
                    }
                }
            if len(proxy_split) == 3:
                proxy_config = {
                    "user_proxy_config": {
                        "proxy_type": proxy_split[0],
                        "proxy_host": proxy_split[1],
                        "proxy_port": proxy_split[2],
                        "proxy_soft": "other"
                    }
                }

        body = {
            "group_id": group_id,
            "fingerprint_config": ADS.generate_fingerprint_config()["fingerprint_config"],
            "user_proxy_config": proxy_config["user_proxy_config"]
        }

        print(body)

        ADS.wait_until_available()
        response = requests.request("POST", url, json=body, headers=ADS.JSON_HEADERS)

        if ADS.DEBUG:
            print(f"Create profile with proxy {proxy} response: ", response.text)

        return response.json()

    @staticmethod
    def delete_profile(profile_id):
        ADS.check_status_okay()

        url = ADS.API_URL + "user/delete"
        body = {
            "user_ids": [profile_id]
        }

        ADS.wait_until_available()
        response = requests.request("POST", url, json=body, headers=ADS.JSON_HEADERS)

        if ADS.DEBUG:
            print(f"Delete profile {profile_id} response: ", response.text)

    @staticmethod
    def clear_all_profiles():
        if ADS.DEBUG:
            print("Clear all profiles started")

        profiles = ADS.list_all_profiles()

        for profile in profiles:
            ADS.stop_browser(profile['user_id'])
            ADS.delete_profile(profile['user_id'])

        if ADS.DEBUG:
            print("Clear all profiles finished")

    @staticmethod
    def start_browser(profile_id):
        url = ADS.API_URL + f'browser/start?user_id={profile_id}&clear_cache_after_closing=1&launch_args=["--disable-notifications"]'

        ADS.wait_until_available()
        response = requests.request("GET", url)

        if ADS.DEBUG:
            print(f"Start browser {profile_id} response: ", response.text)

        return response.json()['data']['ws']['selenium'], response.json()['data']['webdriver']

    @staticmethod
    def stop_browser(profile_id):
        url = ADS.API_URL + f"browser/stop?user_id={profile_id}"

        ADS.wait_until_available()
        response = requests.request("GET", url)

        if ADS.DEBUG:
            print(f"Stop browser {profile_id} response: ", response.text)

    @staticmethod
    def check_browser_status(profile_id):
        url = ADS.API_URL + f"browser/active?user_id={profile_id}"

        ADS.wait_until_available()
        response = requests.request("GET", url)

        if ADS.DEBUG:
            print(f"Check browser status {profile_id} response: ", response.text)

        return response.json()['data']['status']

    @staticmethod
    def update_profile_proxy(profile_id, proxy):
        url = ADS.API_URL + "user/update"

        proxy_split = proxy.split(":")

        proxy_config = ADS.NO_PROXY_CONFIG
        if len(proxy_split) == 5:
            proxy_config = {
                "user_proxy_config": {
                    "proxy_type": proxy_split[0],
                    "proxy_host": proxy_split[1],
                    "proxy_port": proxy_split[2],
                    "proxy_user": proxy_split[3],
                    "proxy_password": proxy_split[4],
                    "proxy_soft": "other"
                }
            }
        if len(proxy_split) == 3:
            proxy_config = {
                "user_proxy_config": {
                    "proxy_type": proxy_split[0],
                    "proxy_host": proxy_split[1],
                    "proxy_port": proxy_split[2],
                    "proxy_soft": "other"
                }
            }

        body = {
            "user_id": profile_id,
            "user_proxy_config": proxy_config["user_proxy_config"]
        }
        print(body)

        ADS.wait_until_available()
        response = requests.request("POST", url, json=body, headers=ADS.JSON_HEADERS)

        if ADS.DEBUG:
            print(f"Update profile proxy {profile_id} response: ", response.text)


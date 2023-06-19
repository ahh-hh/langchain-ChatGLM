from tools import custom_log, save_data
import requests
from requests_html import HTMLSession
import datetime
import time

origin = "https://xueqiu.com"
url = origin + "/statuses/hot/listV2.json"
params = {"since_id": -1, "max_id": -1, "size": 15}
headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cookie": "acw_tc=2760826a16871371498115951e240734b1169546c73927988c563d29d0caec; xq_a_token=1ce5d8004d990273892c085f2b8dc832edd23fde; xqat=1ce5d8004d990273892c085f2b8dc832edd23fde; xq_r_token=1085f78243dfbbacd4186e7b1f3d58d9632367e1; xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOi0xLCJpc3MiOiJ1YyIsImV4cCI6MTY4OTAzNTY5NiwiY3RtIjoxNjg3MTM3MDk2MDYzLCJjaWQiOiJkOWQwbjRBWnVwIn0.eoT2KKvMMbT8qkw8ns87n5UZS-hTAv7lEPJEdrytaQV_ktQjeKAOGJ_8M3L_BJ6yCpdsLVpFWQCoOuBHUfj6wMNJ6r0vV2D6Dpj__61FF8fBL2OGz15nHfBSKIuQJbBYRjKs7mdGoz_MIq9wAGyKptdLITMVb0XjNs5aAkCDvaJQ_qtH37WEs07Dq9Tyq82lHQBeUNoykHrhnbVecnzoRz5hyjWSDgohpEUqAU__vacOCU1__AbXH8_xBL5heCm5POsQYQl3GepT_IwR4LFmXdA6Vw6kT88hcVBrgjbHh0eU0Voc4jiLRUfx8fQ4nPKdSRInzeO-IdRaKTKr_IrMQQ; u=631687137149847; device_id=bcab136b54e6a2a7bf58242da3de623f; Hm_lvt_1db88642e346389874251b5a1eded6e3=1687137151; Hm_lpvt_1db88642e346389874251b5a1eded6e3=1687137151",
    "Host": "xueqiu.com",
    "Referer": origin + "/?category=snb_article",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "elastic-apm-traceparent": "00-5e1120bd0dabdc83d882606b626a44bc-3457b37eada6b61d-01",
    "sec-ch-ua": "'Not.A/Brand';v='8', 'Chromium';v='114', 'Google Chrome';v='114'",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "macOS",
}
yesterday_datetime = datetime.datetime.now()+datetime.timedelta(days=-1)
day_before_yesterday = (datetime.datetime.now()+datetime.timedelta(days=-2)).strftime("%m-%d")
result = ""


def get_data(target):
    global result
    url = origin + target
    session = HTMLSession()
    page_content = session.get(url)
    title = page_content.html.find('.article__bd__title', first=True).text
    post_from = page_content.html.find('.avatar__subtitle', first=True).text + "\n"
    content = page_content.html.find('.article__bd__detail', first=True).text + "\n\n"
    if title:
        title += "\n"
    result += post_from + title + content


def get_list():
    global params
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        custom_log("雪球 listV2 " + str(response.status_code) + " " + response.reason)
    else:
        response_content = response.json()
        is_day_before_yesterday = False
        for item in response_content["items"]:
            if yesterday_datetime.strftime("%m-%d") in item["original_status"]["timeBefore"]:
                is_day_before_yesterday = True
            if yesterday_datetime.strftime("%m-%d") in item["original_status"]["timeBefore"]:
                print(item["original_status"]["target"])
                get_data(item["original_status"]["target"])
        if not is_day_before_yesterday:
            params["max_id"] = response_content["next_max_id"]
            get_list()
        else:
            save_data('雪球热贴' + yesterday_datetime.strftime("%Y-%m-%d"), result)


get_list()

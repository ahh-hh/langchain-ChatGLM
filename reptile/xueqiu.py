from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import random


INDEX_URL = 'https://xueqiu.com/'


def grab_xueqiu():
    browser = webdriver.Chrome()
    browser.maximize_window()
    browser.get(INDEX_URL)
    old_post_list_len = 0

    with open('./list.txt', 'w', encoding='utf-8') as f:
        f.write('')

    while True:
        post_list = browser.find_elements(By.CLASS_NAME, 'AnonymousHome_home__timeline__item_3vU')
        post_list_split = post_list[old_post_list_len:len(post_list)]
        old_post_list_len = len(post_list)
        for post_item in post_list_split:
            item_date = post_item.find_elements(By.CSS_SELECTOR, '.AnonymousHome_auchor_1RR span')[1].text
            item_href = post_item.find_element(By.CLASS_NAME, 'AnonymousHome_a__placeholder_3RZ').get_attribute('href')
            with open('./list.txt', 'a+', encoding='utf-8') as f:
                f.write(item_date + ' ' + item_href + '\n')
            if '2021' in item_date and '07-04' in item_date:
                break
        btn_more = browser.find_element(By.CLASS_NAME, 'AnonymousHome_home__timeline__more_6RI')
        if btn_more.get_attribute('hidden'):
            browser.execute_script('document.documentElement.scrollTop=999999999999999')
        else:
            btn_more.click()
        time.sleep(random.randint(1,5))


grab_xueqiu()
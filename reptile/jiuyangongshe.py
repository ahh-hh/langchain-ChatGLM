from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions
from reptile_tools import get_time_str, save_data
from datetime import datetime
import time


INDEX_URL = 'https://www.jiuyangongshe.com/study_publish'
CURRENT_HOUR = get_time_str(format='%Y-%m-%d %H')
ONE_HOUR_BEFORE = get_time_str(hours=-1, format='%Y-%m-%d %H')


# 是否是置顶帖子
def not_top(post):
    try:
        post.find_element(By.CLASS_NAME, 'topBtn')
        return False
    except exceptions.NoSuchElementException:
        return True


# 获取小时制单位
def get_post_hour(post):
    post_date = post.find_element(By.CLASS_NAME, 'fs13-ash').text
    post_datetime = datetime.strptime(post_date, '%Y-%m-%d %H:%M:%S')
    return post_datetime.strftime('%Y-%m-%d %H')


# 获取帖子详情
def get_post_detail(browser):
    title = browser.find_element(By.CLASS_NAME, 'fs28-bold').text + '\n'
    date = browser.find_element(By.CLASS_NAME, 'date').text + '\n'
    content = browser.find_element(By.TAG_NAME, 'section').text + '\n\n'
    browser.close()
    return title + date + content


# 抓取 韭研公社-研究优选-最新发布
# 抓取逻辑：每小时59:30秒抓取当前一小时内发布的帖子
def grab_jiuyangongshe():
    browser = webdriver.Chrome()
    # browser.maximize_window()
    browser.get(INDEX_URL)
    # 存储原始窗口的 ID
    original_window = browser.current_window_handle
    # 设置等待
    wait = WebDriverWait(browser, 100)
    # 抓取结果
    result = ''

    while True:
        post_list = browser.find_elements(By.CSS_SELECTOR, '.community-bar li')
        has_after_one_hour = False
        for post_item in post_list:
            if not_top(post_item) and get_post_hour(post_item) == ONE_HOUR_BEFORE:
                has_after_one_hour = True
                break
        if has_after_one_hour:
            for post_item in post_list:
                if not_top(post_item) and get_post_hour(post_item) == CURRENT_HOUR:
                    # 打开帖子
                    post_item.click()
                    # 等待新窗口或标签页
                    wait.until(EC.number_of_windows_to_be(2))
                    browser.switch_to.window(browser.window_handles[1])
                    grab_result = get_post_detail(browser)
                    result += grab_result
                    browser.switch_to.window(original_window)
            break
        else:
            try:
                btn_more = browser.find_element(By.CLASS_NAME, 'jc_more')
                btn_more.click()
            except exceptions.NoSuchElementException:
                browser.execute_script('document.documentElement.scrollTop=99999')
            time.sleep(2)

    save_data('韭研公社 研选 ' + get_time_str(format='%Y-%m-%d %-H') + '时', result)

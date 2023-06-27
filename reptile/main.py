import schedule
import time
from xueqiu import grab_xueqiu
from jiuyangongshe import grab_jiuyangongshe


def grab():
    grab_xueqiu()
    grab_jiuyangongshe()


if __name__ == '__main__':
    schedule.every().day.at("02:00").do(grab)
    while True:
        schedule.run_pending()
        time.sleep(1)

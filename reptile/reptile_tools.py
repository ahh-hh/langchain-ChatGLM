import os
from datetime import datetime
from chains.local_doc_qa import LocalDocQA
from configs.model_config import (KB_ROOT_PATH, EMBEDDING_DEVICE,
                                  EMBEDDING_MODEL,
                                  VECTOR_SEARCH_TOP_K, LLM_HISTORY_LEN)

FOLDER_LOG = "reptile/log"
KNOWLEDGE_BASE_ID = "common"

# 获取当前日期年月日
def get_today_str():
    today = datetime.now()
    return today.strftime('%Y-%m-%d')


# 判断是否存在文件夹，如果不存在则创建
def exist_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)


# 存储本地日志方法
def custom_log(first_msg, second_msg=""):
    exist_folder(FOLDER_LOG)
    file = r'' + FOLDER_LOG + '/' + get_today_str() + '.txt'
    with open(file, 'a+', encoding='utf-8') as f:
        f.write(datetime.now().strftime('%Y/%m/%d %X') + ' :\n')
        f.write(first_msg + '\n')
        if second_msg:
            f.write(second_msg + '\n\n')
        else:
            f.write('\n')


def get_folder_path(local_doc_id: str):
    return os.path.join(KB_ROOT_PATH, local_doc_id, "content")


def get_vs_path(local_doc_id: str):
    return os.path.join(KB_ROOT_PATH, local_doc_id, "vector_store")


# 存储抓取数据
def save_data(file_name, data_str):
    saved_path = get_folder_path(KNOWLEDGE_BASE_ID)
    if not os.path.exists(saved_path):
        os.makedirs(saved_path)
    file_path = os.path.join(saved_path, file_name)
    with open(file_path, 'a+', encoding='utf-8') as f:
        f.write(data_str)

    vs_path = get_vs_path(KNOWLEDGE_BASE_ID)
    local_doc_qa = LocalDocQA()
    local_doc_qa.init_cfg(
        embedding_model=EMBEDDING_MODEL,
        embedding_device=EMBEDDING_DEVICE,
        top_k=VECTOR_SEARCH_TOP_K,
    )
    loaded_files = local_doc_qa.init_knowledge_vector_store([file_path], vs_path)
    if len(loaded_files) <= 0:
        custom_log("save_data失败", "文件名称：" + file_name)

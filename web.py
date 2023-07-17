import gradio as gr
import shutil

from chains.local_doc_qa import LocalDocQA
from configs.model_config import *
import nltk
import models.shared as shared
from models.loader.args import parser
from models.loader import LoaderCheckPoint
import os

nltk.data.path = [NLTK_DATA_PATH] + nltk.data.path
base_vs = 'common'


def get_vs_list():
    lst_default = ["新建知识库"]
    if not os.path.exists(KB_ROOT_PATH):
        return lst_default
    lst = os.listdir(KB_ROOT_PATH)
    if not lst:
        return lst_default
    lst.sort()
    return lst_default + lst


embedding_model_dict_list = list(embedding_model_dict.keys())

llm_model_dict_list = list(llm_model_dict.keys())

local_doc_qa = LocalDocQA()

flag_csv_logger = gr.CSVLogger()


def get_answer(query, vs_path, history, mode, score_threshold=VECTOR_SEARCH_SCORE_THRESHOLD,
               vector_search_top_k=VECTOR_SEARCH_TOP_K, chunk_conent: bool = True,
               chunk_size=CHUNK_SIZE, streaming: bool = STREAMING):
    if os.path.exists(vs_path):
        if mode == '知识库测试':
            print('score_threshold', score_threshold)
            print('vector_search_top_k', vector_search_top_k)
            print('chunk_conent', chunk_conent)
            print('chunk_size', chunk_size)
            resp, prompt = local_doc_qa.get_knowledge_based_conent_test(query=query, vs_path=vs_path,
                                                                        score_threshold=score_threshold,
                                                                        vector_search_top_k=vector_search_top_k,
                                                                        chunk_conent=chunk_conent,
                                                                        chunk_size=chunk_size)
            if not resp["source_documents"]:
                yield history + [[query,
                                    "根据您的设定，没有匹配到任何内容，请确认您设置的知识相关度 Score 阈值是否过小或其他参数是否正确。"]], ""
            else:
                source = "\n".join(
                    [
                        f"""<details open> <summary>【知识相关度 Score】：{doc.metadata["score"]} - 【出处{i + 1}】：  {os.path.split(doc.metadata["source"])[-1]} </summary>\n"""
                        f"""{doc.page_content}\n"""
                        f"""</details>"""
                        for i, doc in
                        enumerate(resp["source_documents"])])
                history.append([query, "以下内容为知识库中满足设置条件的匹配结果：\n\n" + source])
                yield history, ""
        else:
            for resp, history in local_doc_qa.get_knowledge_based_answer(
                    query=query, vs_path=vs_path, chat_history=history, streaming=streaming):
                source = "\n\n"
                source += "".join(
                    [f"""<details> <summary>出处 [{i + 1}] {os.path.split(doc.metadata["source"])[-1]}</summary>\n"""
                    f"""{doc.page_content}\n"""
                    f"""</details>"""
                    for i, doc in
                    enumerate(resp["source_documents"])])
                history[-1][-1] += source
                yield history, ""
    else:
        yield history + [[query,
                            "请选择知识库后进行测试，当前未选择知识库。"]], ""
    logger.info(f"flagging: username={FLAG_USER_NAME},query={query},vs_path={vs_path},history={history}")
    flag_csv_logger.flag([query, vs_path, history], username=FLAG_USER_NAME)


def init_model():
    args = parser.parse_args()

    args_dict = vars(args)
    shared.loaderCheckPoint = LoaderCheckPoint(args_dict)
    llm_model_ins = shared.loaderLLM()
    llm_model_ins.set_history_len(LLM_HISTORY_LEN)
    try:
        local_doc_qa.init_cfg(llm_model=llm_model_ins)
        generator = local_doc_qa.llm.generatorAnswer("你好")
        for answer_result in generator:
            print(answer_result.llm_output)
        vs_path = os.path.join(KB_ROOT_PATH, base_vs, "vector_store")
        if "index.faiss" in os.listdir(vs_path):
            reply = f"已加载知识库{base_vs}，请开始提问"
            logger.info(reply)
            return reply
        else:
            reply = f"已选择知识库{base_vs}，当前知识库中未上传文件，请先上传文件后，再开始提问"
            logger.info(reply)
            return reply
    except Exception as e:
        logger.error(e)
        reply = """模型未成功加载，请到页面左上角"模型配置"选项卡中重新选择后点击"加载模型"按钮"""
        if str(e) == "Unknown platform: darwin":
            logger.info("该报错可能因为您使用的是 macOS 操作系统，需先下载模型至本地后执行 Web UI，具体方法请参考项目 README 中本地部署方法及常见问题："
                        " https://github.com/imClumsyPanda/langchain-ChatGLM")
        else:
            logger.info(reply)
        return reply


def reinit_model(llm_model, embedding_model, llm_history_len, no_remote_model, use_ptuning_v2, use_lora, top_k,
                 history):
    try:
        llm_model_ins = shared.loaderLLM(llm_model, no_remote_model, use_ptuning_v2)
        llm_model_ins.history_len = llm_history_len
        local_doc_qa.init_cfg(llm_model=llm_model_ins,
                              embedding_model=embedding_model,
                              top_k=top_k)
        model_status = """模型已成功重新加载，可以开始对话，或从右侧选择模式后开始对话"""
        logger.info(model_status)
    except Exception as e:
        logger.error(e)
        model_status = """模型未成功重新加载，请到页面左上角"模型配置"选项卡中重新选择后点击"加载模型"按钮"""
        logger.info(model_status)
    return history + [[None, model_status]]


def get_vector_store(vs_id, files, sentence_size, history, one_conent, one_content_segmentation):
    vs_path = os.path.join(KB_ROOT_PATH, vs_id, "vector_store")
    filelist = []
    if local_doc_qa.llm and local_doc_qa.embeddings:
        if isinstance(files, list):
            for file in files:
                filename = os.path.split(file.name)[-1]
                shutil.move(file.name, os.path.join(KB_ROOT_PATH, vs_id, "content", filename))
                filelist.append(os.path.join(KB_ROOT_PATH, vs_id, "content", filename))
            vs_path, loaded_files = local_doc_qa.init_knowledge_vector_store(filelist, vs_path, sentence_size)
        else:
            vs_path, loaded_files = local_doc_qa.one_knowledge_add(vs_path, files, one_conent, one_content_segmentation,
                                                                   sentence_size)
        if len(loaded_files):
            file_status = f"已添加 {'、'.join([os.path.split(i)[-1] for i in loaded_files if i])} 内容至知识库，请开始提问"
        else:
            file_status = "文件未成功加载，请重新上传文件"
    else:
        file_status = "模型未完成加载，请先在加载模型后再导入文件"
        vs_path = None
    logger.info(file_status)
    return vs_path, None, history + [[None, file_status]], \
           gr.update(choices=local_doc_qa.list_file_from_vector_store(vs_path), value=[])


def change_vs_name_input(vs_id, history):
    if vs_id == "新建知识库":
        return gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), None, history,\
                gr.update(choices=[]), gr.update(visible=False)
    else:
        vs_path = os.path.join(KB_ROOT_PATH, vs_id, "vector_store")
        if "index.faiss" in os.listdir(vs_path):
            file_status = f"已加载知识库{vs_id}，请开始提问"
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), \
                   vs_path, history + [[None, file_status]], \
                   gr.update(choices=local_doc_qa.list_file_from_vector_store(vs_path), value=[]), \
                   gr.update(visible=True)
        else:
            file_status = f"已选择知识库{vs_id}，当前知识库中未上传文件，请先上传文件后，再开始提问"
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), \
                   vs_path, history + [[None, file_status]], \
                   gr.update(choices=[], value=[]), gr.update(visible=True, value=[])


def change_chunk_conent(mode, label_conent, history):
    conent = ""
    if "chunk_conent" in label_conent:
        conent = "搜索结果上下文关联"
    elif "one_content_segmentation" in label_conent:  # 这里没用上，可以先留着
        conent = "内容分段入库"

    if mode:
        return gr.update(visible=True), history + [[None, f"【已开启{conent}】"]]
    else:
        return gr.update(visible=False), history + [[None, f"【已关闭{conent}】"]]


def add_vs_name(vs_name, chatbot):
    if vs_name in get_vs_list():
        vs_status = "与已有知识库名称冲突，请重新选择其他名称后提交"
        chatbot = chatbot + [[None, vs_status]]
        return gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(
            visible=False), chatbot, gr.update(visible=False)
    else:
        # 新建上传文件存储路径
        if not os.path.exists(os.path.join(KB_ROOT_PATH, vs_name, "content")):
            os.makedirs(os.path.join(KB_ROOT_PATH, vs_name, "content"))
        # 新建向量库存储路径
        if not os.path.exists(os.path.join(KB_ROOT_PATH, vs_name, "vector_store")):
            os.makedirs(os.path.join(KB_ROOT_PATH, vs_name, "vector_store"))
        vs_status = f"""已新增知识库"{vs_name}",将在上传文件并载入成功后进行存储。请在开始对话前，先完成文件上传。 """
        chatbot = chatbot + [[None, vs_status]]
        return gr.update(visible=True, choices=get_vs_list(), value=vs_name), gr.update(
            visible=False), gr.update(visible=False), gr.update(visible=True), chatbot, gr.update(visible=True)


# 自动化加载固定文件间中文件
def reinit_vector_store(vs_id, history):
    try:
        shutil.rmtree(os.path.join(KB_ROOT_PATH, vs_id, "vector_store"))
        vs_path = os.path.join(KB_ROOT_PATH, vs_id, "vector_store")
        sentence_size = gr.Number(value=SENTENCE_SIZE, precision=0,
                                  label="文本入库分句长度限制",
                                  interactive=True, visible=True)
        vs_path, loaded_files = local_doc_qa.init_knowledge_vector_store(os.path.join(KB_ROOT_PATH, vs_id, "content"),
                                                                         vs_path, sentence_size)
        model_status = """知识库构建成功"""
    except Exception as e:
        logger.error(e)
        model_status = """知识库构建未成功"""
        logger.info(model_status)
    return history + [[None, model_status]]


def refresh_vs_list():
    vs_path = os.path.join(KB_ROOT_PATH, base_vs, "vector_store")
    return gr.update(choices=get_vs_list()), gr.update(choices=local_doc_qa.list_file_from_vector_store(vs_path), value=[])

def delete_file(vs_id, files_to_delete, chatbot):
    vs_path = os.path.join(KB_ROOT_PATH, vs_id, "vector_store")
    content_path = os.path.join(KB_ROOT_PATH, vs_id, "content")
    docs_path = [os.path.join(content_path, file) for file in files_to_delete]
    status = local_doc_qa.delete_file_from_vector_store(vs_path=vs_path,
                                                        filepath=docs_path)
    if "fail" not in status:
        for doc_path in docs_path:
            if os.path.exists(doc_path):
                os.remove(doc_path)
    rested_files = local_doc_qa.list_file_from_vector_store(vs_path)
    if "fail" in status:
        vs_status = "文件删除失败。"
    elif len(rested_files)>0:
        vs_status = "文件删除成功。"
    else:
        vs_status = f"文件删除成功，知识库{vs_id}中无已上传文件，请先上传文件后，再开始提问。"
    logger.info(",".join(files_to_delete)+vs_status)
    chatbot = chatbot + [[None, vs_status]]
    return gr.update(choices=local_doc_qa.list_file_from_vector_store(vs_path), value=[]), chatbot


def delete_vs(vs_id, chatbot):
    try:
        shutil.rmtree(os.path.join(KB_ROOT_PATH, vs_id))
        status = f"成功删除知识库{vs_id}"
        logger.info(status)
        chatbot = chatbot + [[None, status]]
        return gr.update(choices=get_vs_list(), value=get_vs_list()[0]), gr.update(visible=True), gr.update(visible=True), \
               gr.update(visible=False), chatbot, gr.update(visible=False)
    except Exception as e:
        logger.error(e)
        status = f"删除知识库{vs_id}失败"
        chatbot = chatbot + [[None, status]]
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), \
               gr.update(visible=True), chatbot, gr.update(visible=True)

block_css = """.importantButton {
    background: linear-gradient(45deg, #7e0570,#5d1c99, #6e00ff) !important;
    border: none !important;
}
.importantButton:hover {
    background: linear-gradient(45deg, #ff00e0,#8500ff, #6e00ff) !important;
    border: none !important;
}"""


# 初始化消息
model_status = init_model()

default_theme_args = dict(
    font=["Source Sans Pro", 'ui-sans-serif', 'system-ui', 'sans-serif'],
    font_mono=['IBM Plex Mono', 'ui-monospace', 'Consolas', 'monospace'],
)

with gr.Blocks(css=block_css, theme=gr.themes.Default(**default_theme_args)) as demo:
    vs_path, file_status, model_status = gr.State(
        os.path.join(KB_ROOT_PATH, base_vs, "vector_store")), gr.State(""), gr.State(
        model_status)
    with gr.Row():
        with gr.Column(scale=10):
            chatbot = gr.Chatbot([[None, model_status.value]],
                                    elem_id="chat-box",
                                    show_label=False).style(height=750)
            query = gr.Textbox(show_label=False,
                                placeholder="请输入提问内容，按回车进行提交").style(container=False)
        with gr.Column(scale=5):
            mode = gr.Radio(["知识库问答", "知识库测试"],
                                label="请选择使用模式",
                                value="知识库问答", )
            knowledge_set = gr.Accordion("知识库设定", visible=True, open=False)
            vs_setting = gr.Accordion("配置知识库", visible=True)
            with knowledge_set:
                score_threshold = gr.Number(value=VECTOR_SEARCH_SCORE_THRESHOLD,
                                            label="知识相关度 Score 阈值，分值越低匹配度越高",
                                            precision=0,
                                            interactive=True)
                vector_search_top_k = gr.Number(value=VECTOR_SEARCH_TOP_K, precision=0,
                                                label="获取知识库内容条数", interactive=True)
                chunk_conent = gr.Checkbox(value=False,
                                            label="是否启用上下文关联",
                                            interactive=True)
                chunk_sizes = gr.Number(value=CHUNK_SIZE, precision=0,
                                        label="匹配单段内容的连接上下文后最大长度",
                                        interactive=True, visible=False)
                chunk_conent.change(fn=change_chunk_conent,
                                    inputs=[chunk_conent, gr.Textbox(value="chunk_conent", visible=False), chatbot],
                                    outputs=[chunk_sizes, chatbot])
            with vs_setting:
                vs_refresh = gr.Button("更新已有知识库选项")
                select_vs = gr.Dropdown(get_vs_list(),
                                        label="请选择要加载的知识库",
                                        interactive=True,
                                        value=base_vs)
                vs_name = gr.Textbox(label="请输入新建知识库名称，当前知识库命名暂不支持中文",
                                        lines=1,
                                        interactive=True,
                                        visible=False)
                vs_add = gr.Button(value="添加至知识库选项", visible=False)
                vs_delete = gr.Button("删除本知识库", visible=True)
                file2vs = gr.Column(visible=True)
                with file2vs:
                    # load_vs = gr.Button("加载知识库")
                    gr.Markdown("向知识库中添加文件")
                    sentence_size_set = gr.Accordion("文本入库分句长度限制", visible=True, open=False)
                    with sentence_size_set:
                        sentence_size = gr.Number(value=SENTENCE_SIZE, precision=0,
                                                    label="",
                                                    interactive=True, visible=True)
                    with gr.Tab("上传文件"):
                        files = gr.File(label="添加文件",
                                        file_types=['.txt', '.md', '.docx', '.pdf'],
                                        file_count="multiple",
                                        show_label=False
                                        )
                        load_file_button = gr.Button("上传文件并加载知识库")
                    with gr.Tab("上传文件夹"):
                        folder_files = gr.File(label="添加文件",
                                                # file_types=['.txt', '.md', '.docx', '.pdf'],
                                                file_count="directory",
                                                show_label=False)
                        load_folder_button = gr.Button("上传文件夹并加载知识库")
                    with gr.Tab("删除文件"):
                        files_to_delete = gr.CheckboxGroup(choices=[],
                                                            label="请从知识库已有文件中选择要删除的文件",
                                                            interactive=True)
                        delete_file_button = gr.Button("从知识库中删除选中文件")
                # 将上传的文件保存到content文件夹下,并更新下拉框
                vs_refresh.click(fn=refresh_vs_list,
                                    inputs=[],
                                    outputs=select_vs)
                vs_add.click(fn=add_vs_name,
                                inputs=[vs_name, chatbot],
                                outputs=[select_vs, vs_name, vs_add, file2vs, chatbot, vs_delete])
                vs_delete.click(fn=delete_vs,
                                    inputs=[select_vs, chatbot],
                                    outputs=[select_vs, vs_name, vs_add, file2vs, chatbot, vs_delete])
                select_vs.change(fn=change_vs_name_input,
                                    inputs=[select_vs, chatbot],
                                    outputs=[vs_name, vs_add, file2vs, vs_path, chatbot, files_to_delete, vs_delete])
                load_file_button.click(get_vector_store,
                                        show_progress=True,
                                        inputs=[select_vs, files, sentence_size, chatbot, vs_add, vs_add],
                                        outputs=[vs_path, files, chatbot, files_to_delete], )
                load_folder_button.click(get_vector_store,
                                            show_progress=True,
                                            inputs=[select_vs, folder_files, sentence_size, chatbot, vs_add,
                                                    vs_add],
                                            outputs=[vs_path, files, chatbot, files_to_delete], )
                flag_csv_logger.setup([query, vs_path, chatbot], "flagged")
                query.submit(get_answer,
                                [query, vs_path, chatbot, mode, score_threshold, vector_search_top_k, chunk_conent,
                                chunk_sizes],
                                [chatbot, query])
                delete_file_button.click(delete_file,
                                            show_progress=True,
                                            inputs=[select_vs, files_to_delete, chatbot],
                                            outputs=[files_to_delete, chatbot])
    demo.load(
        fn=refresh_vs_list,
        inputs=None,
        outputs=[select_vs, files_to_delete],
        queue=True,
        show_progress=False,
    )

(demo
    .queue(concurrency_count=3)
    .launch(server_name='0.0.0.0',
            server_port=6006,
            show_api=False,
            share=False,
            inbrowser=False))

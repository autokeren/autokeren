from autokeren.tools.repo_map import RepoMapTool


def test_repo_map_python_parsing(tmp_path):
    py_content = """
class MyClass(Base):
    def __init__(self, x: int):
        self.x = x
        
    async def process(self):
        pass

def global_func(a, b=1):
    return a + b
"""
    py_file = tmp_path / "test.py"
    py_file.write_text(py_content, encoding="utf-8")

    tool = RepoMapTool(tmp_path)
    res_summary, res_symbols = tool._parse_file(py_file)
    assert "class MyClass(Base):" in res_summary
    assert "def __init__(self, x)" in res_summary
    assert "def async process(self)" in res_summary
    assert "def global_func(a, b)" in res_summary
    assert "MyClass" in res_symbols
    assert "process" in res_symbols
    assert "global_func" in res_symbols


def test_repo_map_go_parsing(tmp_path):
    go_content = """
package mypkg

import "fmt"

func (s *Server) Start(port int) error {
    return nil
}

func HelloWorld() {
    fmt.Println("Hi")
}
"""
    go_file = tmp_path / "test.go"
    go_file.write_text(go_content, encoding="utf-8")

    tool = RepoMapTool(tmp_path)
    res_summary, res_symbols = tool._parse_file(go_file)
    assert "package mypkg" in res_summary
    assert "func (s *Server) Start(port int) error" in res_summary
    assert "func HelloWorld()" in res_summary
    assert "mypkg" in res_symbols
    assert "Start" in res_symbols
    assert "HelloWorld" in res_symbols


def test_repo_map_js_ts_parsing(tmp_path):
    js_content = """
export default class Router {
    constructor() {}
}

async function handleRequest(req) {
    return true;
}

const formatData = (item) => {
    return item;
}
"""
    js_file = tmp_path / "test.js"
    js_file.write_text(js_content, encoding="utf-8")

    tool = RepoMapTool(tmp_path)
    res_summary, res_symbols = tool._parse_file(js_file)
    assert "class Router" in res_summary
    assert "function handleRequest()" in res_summary
    assert "const formatData = () =>" in res_summary
    assert "Router" in res_symbols
    assert "handleRequest" in res_symbols
    assert "formatData" in res_symbols


def test_repo_map_full_run(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "src" / "index.js").write_text("function init() {}", encoding="utf-8")
    (tmp_path / "node_modules" / "some_package.js").write_text("function bad() {}", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Hello", encoding="utf-8")

    tool = RepoMapTool(tmp_path)
    res = tool.run()
    assert res.ok
    assert "src/index.js" in res.output
    assert "README.md" in res.output
    assert "node_modules" not in res.output

    # Cek bahwa berkas cache dibuat
    assert (tmp_path / ".ak-repomap.cache").exists()


def test_repo_map_relevance_filtering(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def login_user(username, password):\n    pass", encoding="utf-8")
    (tmp_path / "src" / "utils.py").write_text("def helper_fn():\n    pass", encoding="utf-8")

    tool = RepoMapTool(tmp_path)
    # Jalankan dengan query 'auth login'
    res = tool.run(query="auth login", max_files=1)
    assert res.ok
    
    # File 'auth.py' harus memiliki signature lengkap (karena paling relevan)
    assert "src/auth.py" in res.output
    assert "def login_user(username, password)" in res.output
    
    # File 'utils.py' tidak relevan dengan query, jadi hanya dicantumkan nama berkasnya saja tanpa signature
    assert "src/utils.py" in res.output
    assert "def helper_fn()" not in res.output


def test_repo_map_dependency_graphing(tmp_path):
    (tmp_path / "autokeren").mkdir()
    agent_file = tmp_path / "autokeren" / "agent.py"
    agent_file.write_text("from autokeren.context import SessionContext", encoding="utf-8")
    
    context_file = tmp_path / "autokeren" / "context.py"
    context_file.write_text("class SessionContext:\n    pass", encoding="utf-8")

    tool = RepoMapTool(tmp_path)
    cache = tool.update_index()
    
    agent_info = cache["files"]["autokeren/agent.py"]
    assert "autokeren/context.py" in agent_info["dependencies"]

    res = tool.run(query="agent", max_files=2)
    assert res.ok
    assert "autokeren/context.py" in res.output
    assert "class SessionContext" in res.output

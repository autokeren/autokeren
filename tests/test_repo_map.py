from autokeren.tools.repo_map import RepoMapTool


def test_repo_map_python_parsing(tmp_path):
    # Buat file python simulasi
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
    res = tool._parse_file(py_file)
    assert "class MyClass(Base):" in res
    assert "def __init__(self, x)" in res
    assert "def async process(self)" in res
    assert "def global_func(a, b)" in res


def test_repo_map_go_parsing(tmp_path):
    # Buat file go simulasi
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
    res = tool._parse_file(go_file)
    assert "package mypkg" in res
    assert "func (s *Server) Start(port int) error" in res
    assert "func HelloWorld()" in res


def test_repo_map_js_ts_parsing(tmp_path):
    # Buat file js/ts simulasi
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
    res = tool._parse_file(js_file)
    assert "class Router" in res
    assert "function handleRequest()" in res
    assert "const formatData = () =>" in res


def test_repo_map_full_run(tmp_path):
    # Setup tree folder
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
    # Node modules harus diabaikan
    assert "node_modules" not in res.output

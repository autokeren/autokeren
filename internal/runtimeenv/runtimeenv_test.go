package runtimeenv

import (
	"reflect"
	"strings"
	"testing"
)

func TestDetectWindowsUsesWindowsShellAndCapabilities(t *testing.T) {
	info := Detect("windows", "amd64", func(name string) bool { return name == "git" || name == "npx" })
	if info.Shell != "cmd.exe /D /S /C" || info.CommandStyle != "Windows Command Prompt" {
		t.Fatalf("unexpected Windows shell: %#v", info)
	}
	program, arguments := info.ShellInvocation("dir")
	if program != "cmd.exe" || !reflect.DeepEqual(arguments, []string{"/D", "/S", "/C", "dir"}) {
		t.Fatalf("unexpected Windows invocation: %s %#v", program, arguments)
	}
	if !strings.Contains(info.PromptDescription(), "OS: windows") || !strings.Contains(info.PromptDescription(), "git, npx") {
		t.Fatalf("runtime description incomplete: %s", info.PromptDescription())
	}
}

func TestDetectUnixUsesPOSIXShell(t *testing.T) {
	info := Detect("linux", "arm64", func(string) bool { return true })
	program, arguments := info.ShellInvocation("printf hello")
	if info.Shell != "sh -lc" || program != "sh" || !reflect.DeepEqual(arguments, []string{"-lc", "printf hello"}) {
		t.Fatalf("unexpected Unix invocation: %#v %s %#v", info, program, arguments)
	}
}

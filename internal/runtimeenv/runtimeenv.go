package runtimeenv

import (
	"runtime"
	"sort"
	"strings"
)

var trackedExecutables = []string{"git", "go", "node", "npm", "npx", "wrangler", "python", "python3", "pip", "pip3", "pipx", "docker"}

type Info struct {
	OS                   string   `json:"os"`
	Architecture         string   `json:"architecture"`
	Shell                string   `json:"shell"`
	CommandStyle         string   `json:"command_style"`
	AvailableExecutables []string `json:"available_executables"`
	MissingExecutables   []string `json:"missing_executables"`
}

func Current() Info {
	return Detect(runtime.GOOS, runtime.GOARCH, executableAvailable)
}

func Detect(goos, architecture string, available func(string) bool) Info {
	info := Info{OS: strings.ToLower(strings.TrimSpace(goos)), Architecture: strings.TrimSpace(architecture)}
	if info.OS == "" {
		info.OS = "unknown"
	}
	if info.Architecture == "" {
		info.Architecture = "unknown"
	}
	if info.OS == "windows" {
		info.Shell = "cmd.exe /D /S /C"
		info.CommandStyle = "Windows Command Prompt"
	} else {
		info.Shell = "sh -lc"
		info.CommandStyle = "POSIX shell"
	}
	for _, name := range trackedExecutables {
		if available != nil && available(name) {
			info.AvailableExecutables = append(info.AvailableExecutables, name)
		} else {
			info.MissingExecutables = append(info.MissingExecutables, name)
		}
	}
	sort.Strings(info.AvailableExecutables)
	sort.Strings(info.MissingExecutables)
	return info
}

func (i Info) ShellInvocation(command string) (string, []string) {
	if strings.EqualFold(i.OS, "windows") {
		return "cmd.exe", []string{"/D", "/S", "/C", command}
	}
	return "sh", []string{"-lc", command}
}

func (i Info) PromptDescription() string {
	available := "tidak ada command developer terdeteksi"
	if len(i.AvailableExecutables) > 0 {
		available = strings.Join(i.AvailableExecutables, ", ")
	}
	missing := "tidak ada"
	if len(i.MissingExecutables) > 0 {
		missing = strings.Join(i.MissingExecutables, ", ")
	}
	return "OS: " + i.OS + "; arsitektur: " + i.Architecture + "; shell run_shell: " + i.Shell + " (" + i.CommandStyle + "). Command terdeteksi: " + available + ". Command belum terdeteksi: " + missing + "."
}

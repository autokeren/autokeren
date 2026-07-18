//go:build windows

package ghost

import (
	"os/exec"
	"path/filepath"
	"strings"

	"golang.org/x/sys/windows"
)

func processAlive(pid int) bool {
	if pid <= 0 {
		return false
	}
	process, err := windows.OpenProcess(windows.SYNCHRONIZE|windows.PROCESS_QUERY_LIMITED_INFORMATION, false, uint32(pid))
	if err != nil {
		return false
	}
	defer windows.CloseHandle(process)
	state, err := windows.WaitForSingleObject(process, 0)
	return err == nil && state == uint32(windows.WAIT_TIMEOUT)
}

func processIsAutokeren(pid int) bool {
	identity, ok := readProcessIdentity(pid)
	if !ok {
		return false
	}
	name := strings.ToLower(filepath.Base(identity.Executable))
	return name == "autokeren.exe" || name == "autokeren-cli.exe" || name == "ak.exe"
}

func readProcessIdentity(pid int) (processIdentity, bool) {
	if pid <= 0 {
		return processIdentity{}, false
	}
	process, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, uint32(pid))
	if err != nil {
		return processIdentity{}, false
	}
	defer windows.CloseHandle(process)
	path := make([]uint16, 32768)
	size := uint32(len(path))
	if err := windows.QueryFullProcessImageName(process, 0, &path[0], &size); err != nil {
		return processIdentity{}, false
	}
	var created, exited, kernel, user windows.Filetime
	if err := windows.GetProcessTimes(process, &created, &exited, &kernel, &user); err != nil {
		return processIdentity{}, false
	}
	return processIdentity{Executable: windows.UTF16ToString(path[:size]), StartedAt: created.Nanoseconds()}, true
}

func processMatches(info *GhostAgentInfo) bool {
	if info == nil || info.PID <= 0 || info.BinaryPath == "" || info.ProcessStart == 0 {
		return false
	}
	identity, ok := readProcessIdentity(info.PID)
	if !ok || identity.StartedAt != info.ProcessStart {
		return false
	}
	return strings.EqualFold(filepath.Clean(identity.Executable), filepath.Clean(info.BinaryPath))
}

func terminatePID(pid int) {
	if process, err := windows.OpenProcess(windows.PROCESS_TERMINATE, false, uint32(pid)); err == nil {
		defer windows.CloseHandle(process)
		_ = windows.TerminateProcess(process, 1)
	}
}

func configureProcessGroup(_ *exec.Cmd) {}
func terminateProcessGroup(cmd *exec.Cmd) {
	if cmd.Process != nil {
		_ = cmd.Process.Kill()
	}
}

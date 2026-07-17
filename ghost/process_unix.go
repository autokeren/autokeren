//go:build unix

package ghost

import (
	"os"
	"os/exec"
	"syscall"
)

func processAlive(pid int) bool {
	if pid <= 0 {
		return false
	}
	process, err := os.FindProcess(pid)
	if err != nil {
		return false
	}
	return process.Signal(syscall.Signal(0)) == nil
}

func terminatePID(pid int) {
	if pid > 0 {
		_ = syscall.Kill(-pid, syscall.SIGTERM)
	}
}

func configureProcessGroup(cmd *exec.Cmd) { cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true} }
func terminateProcessGroup(cmd *exec.Cmd) {
	if cmd.Process != nil {
		_ = syscall.Kill(-cmd.Process.Pid, syscall.SIGTERM)
	}
}

//go:build windows

package ghost

import "os/exec"

func configureProcessGroup(_ *exec.Cmd) {}
func terminateProcessGroup(cmd *exec.Cmd) {
	if cmd.Process != nil {
		_ = cmd.Process.Kill()
	}
}

//go:build windows

package ghost

import "os/exec"

func configureProcessGroup(_ *exec.Cmd) {}

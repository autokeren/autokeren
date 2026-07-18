package runtimeenv

import "os/exec"

func executableAvailable(name string) bool {
	_, err := exec.LookPath(name)
	return err == nil
}

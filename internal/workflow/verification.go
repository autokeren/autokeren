package workflow

import (
	"fmt"
	"strings"

	"github.com/autokeren/autokeren/internal/tool"
)

type Verification struct {
	kind        string
	inspected   bool
	changed     bool
	red         bool
	green       bool
	deployed    bool
	verified    bool
	pendingTest bool
}

func NewVerification(input string) *Verification {
	lower := strings.ToLower(input)
	switch {
	case strings.Contains(lower, "jalankan workflow tdd"):
		return &Verification{kind: "tdd"}
	case strings.Contains(lower, "user minta deploy app ke cloudflare"):
		return &Verification{kind: "deploy"}
	default:
		return nil
	}
}

func (v *Verification) ObserveStart(name string, args map[string]any) {
	if v == nil {
		return
	}
	if name == "run_shell" && isTestCommand(fmt.Sprint(args["command"])) {
		v.pendingTest = true
	}
}

func (v *Verification) ObserveEnd(name string, result tool.Result) {
	if v == nil {
		return
	}
	switch name {
	case "read_file", "list_files", "search_code", "repo_map":
		if result.OK {
			v.inspected = true
		}
	case "write_file", "patch_file":
		if result.OK {
			v.changed = true
		}
	case "cf_deploy", "deploy_project":
		if result.OK {
			v.deployed = true
		}
	case "cf_verify":
		if result.OK {
			v.verified = true
		}
	}
	if name == "run_shell" && v.pendingTest {
		if result.OK && v.changed {
			v.green = true
		}
		if !result.OK && !v.changed {
			v.red = true
		}
		v.pendingTest = false
	}
}

func (v *Verification) Report() string {
	if v == nil {
		return ""
	}
	if v.kind == "tdd" {
		missing := missingSteps([]step{{"inspeksi proyek", v.inspected}, {"test merah sebelum implementasi", v.red}, {"perubahan kode", v.changed}, {"test hijau setelah perubahan", v.green}})
		if len(missing) == 0 {
			return "Bukti workflow TDD: terverifikasi (inspeksi, red, perubahan, green)."
		}
		return "Bukti workflow TDD belum lengkap: " + strings.Join(missing, ", ") + ". Jangan klaim selesai sebelum bukti ini ada."
	}
	missing := missingSteps([]step{{"perubahan kode", v.changed}, {"deploy berhasil", v.deployed}, {"verifikasi URL", v.verified}})
	if len(missing) == 0 {
		return "Bukti workflow deploy: terverifikasi (perubahan, deploy, verifikasi URL)."
	}
	return "Bukti workflow deploy belum lengkap: " + strings.Join(missing, ", ") + ". Jangan klaim deploy selesai sebelum bukti ini ada."
}

type step struct {
	name string
	ok   bool
}

func missingSteps(steps []step) []string {
	missing := make([]string, 0, len(steps))
	for _, item := range steps {
		if !item.ok {
			missing = append(missing, item.name)
		}
	}
	return missing
}

func isTestCommand(command string) bool {
	command = strings.ToLower(command)
	return strings.Contains(command, "pytest") || strings.Contains(command, "go test") || strings.Contains(command, "npm test") || strings.Contains(command, "pnpm test") || strings.Contains(command, "yarn test")
}

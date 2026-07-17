package workflow

import (
	"strings"
	"testing"

	"github.com/autokeren/autokeren/internal/tool"
)

func TestTDDVerificationRequiresRedChangeAndGreen(t *testing.T) {
	verification := NewVerification(tddPrompt("calc.go", "tambah pajak"))
	verification.ObserveEnd("read_file", tool.Result{OK: true})
	verification.ObserveStart("run_shell", map[string]any{"command": "go test ./..."})
	verification.ObserveEnd("run_shell", tool.Result{OK: false})
	verification.ObserveEnd("patch_file", tool.Result{OK: true})
	verification.ObserveStart("run_shell", map[string]any{"command": "go test ./..."})
	verification.ObserveEnd("run_shell", tool.Result{OK: true})
	if report := verification.Report(); !strings.Contains(report, "terverifikasi") {
		t.Fatalf("unexpected report: %q", report)
	}
}

func TestDeployVerificationDoesNotClaimSuccessWithoutURLCheck(t *testing.T) {
	verification := NewVerification(deployPrompt("catatan"))
	verification.ObserveEnd("write_file", tool.Result{OK: true})
	verification.ObserveEnd("cf_deploy", tool.Result{OK: true})
	if report := verification.Report(); !strings.Contains(report, "verifikasi URL") || strings.Contains(report, "terverifikasi (") {
		t.Fatalf("unexpected report: %q", report)
	}
	verification.ObserveEnd("cf_verify", tool.Result{OK: true})
	if report := verification.Report(); !strings.Contains(report, "terverifikasi") {
		t.Fatalf("unexpected verified report: %q", report)
	}
}

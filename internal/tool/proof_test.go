package tool

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestProofApprovalBindsShipVerdictToCurrentCommit(t *testing.T) {
	root := proofTestRepo(t)
	proof := Proof{Root: root}
	plan := proof.Run(context.Background(), map[string]any{
		"action":   "plan",
		"title":    "Release toko sepatu",
		"criteria": []any{"Halaman utama terbuka"},
	}, nil)
	if !plan.OK {
		t.Fatalf("plan failed: %s", plan.Error)
	}
	proofID := plan.Output.(map[string]any)["proof_id"].(string)
	record := proof.Run(context.Background(), map[string]any{
		"action":        "record",
		"proof_id":      proofID,
		"criterion_num": float64(1),
		"status":        "passed",
		"evidence":      "go test ./...: PASS",
	}, nil)
	if !record.OK {
		t.Fatalf("record failed: %s", record.Error)
	}
	if err := ApprovedProofForCurrentCommit(root, proofID); err == nil || !strings.Contains(err.Error(), "belum disetujui") {
		t.Fatalf("expected waiting approval error, got %v", err)
	}
	approval := proof.Run(context.Background(), map[string]any{"action": "approve", "proof_id": proofID}, nil)
	if !approval.OK {
		t.Fatalf("approval failed: %s", approval.Error)
	}
	if err := ApprovedProofForCurrentCommit(root, proofID); err != nil {
		t.Fatalf("approved proof should be publishable: %v", err)
	}
	proofTestGit(t, root, "commit", "--allow-empty", "-m", "change after approval")
	if err := ApprovedProofForCurrentCommit(root, proofID); err == nil || !strings.Contains(err.Error(), "stale") {
		t.Fatalf("expected stale proof error, got %v", err)
	}
}

func TestPublishAppBlocksSafeDeployWithoutApprovedProof(t *testing.T) {
	result := (PublishApp{Root: t.TempDir(), RequireApprovedProof: true}).Run(context.Background(), map[string]any{"name": "toko-sepatu"}, nil)
	if result.OK || !strings.Contains(result.Error, "proof_id") {
		t.Fatalf("safe deploy should require approved proof, got %#v", result)
	}
}

func proofTestRepo(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "app.txt"), []byte("demo\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	proofTestGit(t, root, "init")
	proofTestGit(t, root, "config", "user.name", "Autokeren Test")
	proofTestGit(t, root, "config", "user.email", "test@example.invalid")
	proofTestGit(t, root, "add", "app.txt")
	proofTestGit(t, root, "commit", "-m", "initial")
	return root
}

func proofTestGit(t *testing.T, root string, args ...string) {
	t.Helper()
	command := exec.Command("git", append([]string{"-C", root}, args...)...)
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("git %s failed: %v\n%s", strings.Join(args, " "), err, output)
	}
}

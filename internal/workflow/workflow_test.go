package workflow

import (
	"strings"
	"testing"
)

func TestExpandDeployAndTDD(t *testing.T) {
	deploy, handled, err := Expand("/deploy aplikasi catatan")
	if err != nil || !handled || !strings.Contains(deploy, "scaffold_app") || !strings.Contains(deploy, "publish_app") {
		t.Fatalf("unexpected deploy workflow: %q handled=%t err=%v", deploy, handled, err)
	}
	tdd, handled, err := Expand("/tdd calc.py | tambah pajak")
	if err != nil || !handled || !strings.Contains(tdd, "awalnya gagal") {
		t.Fatalf("unexpected tdd workflow: %q handled=%t err=%v", tdd, handled, err)
	}
}

func TestExpandSpecAnswerAndUsage(t *testing.T) {
	answer, handled, err := Expand("/spec answer pengguna tim kecil")
	if err != nil || !handled || !strings.Contains(answer, "Jawaban pengguna") {
		t.Fatalf("unexpected answer workflow: %q handled=%t err=%v", answer, handled, err)
	}
	_, handled, err = Expand("/deploy")
	if !handled || err == nil {
		t.Fatal("expected deploy usage error")
	}
}

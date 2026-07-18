package ghost

import (
	"strings"
	"testing"
)

func TestAllowedToolsOnlyIncludesKnownMutableCapabilities(t *testing.T) {
	allowed := AllowedTools([]string{"write_file", "unknown", "run_shell", "write_file", " read_file "})
	if strings.Join(allowed, ",") != "run_shell,write_file" {
		t.Fatalf("unexpected allowed tools: %#v", allowed)
	}
}

func TestChildEnvironmentStripsUnrelatedSecrets(t *testing.T) {
	environment := strings.Join(ChildEnvironment([]string{"PATH=/bin", "HOME=/tmp/home", "AUTOKEREN_API_KEY=key", "DATABASE_URL=secret", "GITHUB_TOKEN=secret"}, []string{"patch_file"}), "\n")
	for _, expected := range []string{"PATH=/bin", "HOME=/tmp/home", "AUTOKEREN_API_KEY=key", "AUTOKEREN_GHOST_CHILD=1", "AUTOKEREN_GHOST_ALLOWED_TOOLS=patch_file"} {
		if !strings.Contains(environment, expected) {
			t.Fatalf("environment missing %q: %s", expected, environment)
		}
	}
	for _, forbidden := range []string{"DATABASE_URL", "GITHUB_TOKEN"} {
		if strings.Contains(environment, forbidden) {
			t.Fatalf("environment leaked %q: %s", forbidden, environment)
		}
	}
}

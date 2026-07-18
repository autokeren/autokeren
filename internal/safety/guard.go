package safety

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"

	"go.yaml.in/yaml/v3"
)

var (
	hardReadNames = []string{".ssh", ".aws/credentials", ".aws/config", ".gnupg", "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa", ".pem", ".key", ".pfx", ".p12", ".git-credentials", ".kube/config", ".pgpass", "firebase-adminsdk", "service-account"}
	softReadNames = []string{".env", "config.yaml", "config.yml", "credentials", "credentials.json", "keystore", ".npmrc", ".pypirc", ".netrc", ".docker/config", "secret", "token", "oauth"}
	writeNames    = []string{".ssh", ".bashrc", ".bash_profile", ".profile", ".zshrc", ".bash_aliases", "/etc/", "crontab", ".config/autokeren", ".git/config", ".git/hooks", ".docker", ".kube", "systemd", "init.d", "authorized_keys", "known_hosts", ".npmrc", ".pypirc", ".netrc", ".git-credentials"}
	dangerous     = []pattern{
		{`(?i)\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+/(?:\s|$|\*)`, "rm -rf on root"},
		{`(?i)\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+/(?:home|usr|var|etc|boot|proc|sys)`, "rm -rf on system directory"},
		{`(?i)\bmkfs\b`, "mkfs filesystem format"},
		{`(?i)\bdd\s+.*\b(?:of|if)=/dev/(?:sd|nvme|hd)`, "dd to disk device"},
		{`(?i)>\s*/dev/(?:sd|nvme|hd)`, "write to disk device"},
		{`(?i):\(\)\s*\{\s*:\|:\&\s*\}\s*;:`, "fork bomb"},
		{`(?i)\b--no-preserve-root\b`, "no-preserve-root flag"},
		{`(?i)\bfind\s+/\s+.*-delete\b`, "find / -delete"},
		{`(?i)\bchmod\s+-R\s+777\s+/`, "chmod 777 on root"},
		{`(?i)\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b`, "system power control"},
		{`(?i)\biptables\s+-F\b|\biptables\s+-P\b.*DROP`, "firewall flush or drop policy"},
		{`(?i)\bufw\s+disable\b`, "firewall disable"},
		{`(?i)\bsystemctl\s+(?:stop|disable|mask)\b`, "system service disable"},
		{`(?i)\bmount\s+/dev/\w+\s+/`, "mount device to root"},
		{`(?i)\bumount\s+/(?:\s|$)`, "unmount root"},
		{`(?i)\bcurl\s+.*\|\s*(?:sh|bash|zsh|python|perl|ruby)\b`, "curl piped to shell"},
		{`(?i)\bwget\s+.*\|\s*(?:sh|bash|zsh|python|perl|ruby)\b`, "wget piped to shell"},
		{`(?i)\beval\s*\(`, "eval call"},
		{`(?i)\beval\s+(?:"\$|\$\()`, "eval of variable or subshell"},
		{`(?i)\bbase64\s+.*\|\s*(?:sh|bash|zsh|python)\b`, "base64 piped to shell"},
		{`(?i)\becho\s+.*\|\s*(?:base64|openssl)\s+.*\|\s*(?:sh|bash)`, "encoded content piped to shell"},
		{`(?i)\b(?:nc|ncat)\s+.*\s+-[a-z]*e\b`, "netcat reverse shell"},
		{`(?i)\b(?:bash|sh)\s+-i\s+>&\s*/dev/tcp/`, "shell reverse connection"},
		{`(?i)\bpython\d?\s+-c\s+.*(?:os\.system|subprocess|popen)`, "python command execution"},
		{`(?i)\bperl\s+-e\s+.*(?:system|exec|eval)`, "perl command execution"},
		{`(?i)\bruby\s+-e\s+.*(?:system|exec|eval)`, "ruby command execution"},
		{`(?i)\bsocat\s+.*(?:EXEC|SYSTEM|fork)`, "socat reverse shell"},
		{`(?i)\bscp\s+.*@`, "scp to remote host"},
		{`(?i)\brsync\s+.*@.*::`, "rsync to remote host"},
		{`(?i)\bcrontab\s+(?:-e|-r)\b`, "crontab edit or remove"},
		{`(?i)\becho\s+.*>>\s*.*\.ssh/authorized_keys`, "SSH authorized_keys injection"},
		{`(?i)\becho\s+.*>>\s*.*\.(?:bashrc|profile)`, "shell profile injection"},
		{`(?i)\bexport\s+(?:HOME|PATH|LD_LIBRARY_PATH|PYTHONPATH)\s*=`, "critical environment manipulation"},
		{`(?i)\benv\s+.*\|\s*(?:curl|wget|nc|scp)`, "environment exfiltration"},
		{`(?i)\bcat\s+.*\|\s*(?:curl|wget|nc|scp)\b`, "file exfiltration"},
		{`(?i)\bcp\s+.*\b(?:\.ssh|\.env|\.aws|\.kube|credentials)\b.*\|\s*(?:curl|wget)`, "sensitive copy exfiltration"},
		{`(?i)\btar\s+.*\b(?:\.ssh|\.env|\.aws|\.gnupg)\b.*\|\s*(?:curl|wget|nc)`, "sensitive archive exfiltration"},
		{`(?i)\bsource\s+/dev/stdin`, "source from stdin"},
		{`(?i)\b\.\s+/dev/stdin`, "dot source from stdin"},
		{`(?i)\b(?:curl|wget)\s+.*\$(?:\(|\{)`, "network command variable expansion"},
		{`(?i)\bxargs\s+(?:sh|bash|python|perl)`, "xargs to interpreter"},
		{`(?i)\benv\s+.*xargs\s+(?:sh|bash)`, "environment piped to interpreter"},
		{`(?i)\btee\s+/(?:etc|usr|var|boot|proc|sys)`, "tee to system directory"},
		{`(?i)\bchmod\s+.*\+x.*\|\s*(?:sh|bash)`, "chmod piped to shell"},
		{`(?i)\binstall\s+-m\s*777\s+/`, "install to root with 777"},
		{`(?i)\bchown\s+-R\s+.*\s+/`, "recursive chown on root"},
		{`(?i)\bchattr\s+.*-i\s+/(?:etc|usr|var|boot)`, "immutable system file manipulation"},
		{`(?i)\bkillall\s+-9\b|\bpkill\s+-9\b.*(?:sshd|bash|systemd|init)`, "kill critical process"},
		{`(?i)\bhistory\s+-c\b`, "clear shell history"},
		{`(?i)\bshred\s+.*\.(?:ssh|env|bashrc|profile|bash_history)`, "shred sensitive file"},
		{`(?i)\btruncate\s+-s\s+0\s+.*\.(?:bash_history|zsh_history)`, "truncate shell history"},
	}
	secretPatterns = []pattern{
		{`(?i)(?:api[_-]?key|apikey)["\s]*[:=]\s*["']([\w]{32,})["']`, "API key terdeteksi"},
		{`(?i)(?:secret|token)["\s]*[:=]\s*["']([\w]{32,})["']`, "secret/token terdeteksi"},
		{`AKIA[0-9A-Z]{16}`, "AWS Access Key ID terdeteksi"},
		{`(?i)aws_secret_access_key["\s]*[:=]\s*["']([A-Za-z0-9/+=]{40})["']`, "AWS Secret Key terdeteksi"},
		{`(?i)gh[pousr]_[A-Za-z0-9]{36}`, "GitHub token terdeteksi"},
		{`-----BEGIN (?:RSA |EC )?PRIVATE KEY-----`, "private key terdeteksi"},
		{`(?i)password["\s]*[:=]\s*["']([^"']{8,})["']`, "password hardcoded terdeteksi"},
	}
)

type pattern struct {
	expression string
	reason     string
}

type Policy struct {
	SecurityEnabled      bool
	ScanOnWrite          bool
	BlockOnCritical      bool
	Checks               []string
	GuardianEnabled      bool
	BlockDuplicates      bool
	ScanInterval         int
	EnforcementEnabled   bool
	RulesFile            string
	BlockOnRuleViolation bool
}

type Guard struct {
	root          string
	policy        Policy
	mu            sync.Mutex
	functionIndex map[string][]string
	scanned       bool
	writesScanned int
}

func NewGuard(root string, policy Policy) *Guard {
	resolved, err := filepath.Abs(root)
	if err == nil {
		if realPath, resolveErr := filepath.EvalSymlinks(resolved); resolveErr == nil {
			resolved = realPath
		}
	}
	if policy.ScanInterval <= 0 {
		policy.ScanInterval = 5
	}
	return &Guard{root: filepath.Clean(resolved), policy: policy, functionIndex: map[string][]string{}}
}

func ProjectPath(root, requested string) (string, error) {
	if strings.TrimSpace(requested) == "" {
		requested = "."
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	rootReal := rootAbs
	if resolved, resolveErr := filepath.EvalSymlinks(rootAbs); resolveErr == nil {
		rootReal = resolved
	}
	target := filepath.Clean(filepath.Join(rootAbs, requested))
	if !within(rootAbs, target) {
		return "", errors.New("path escapes project root")
	}
	resolvedTarget, err := resolveTarget(target)
	if err != nil {
		return "", err
	}
	if !within(rootReal, resolvedTarget) {
		return "", errors.New("path symlink escapes project root")
	}
	return target, nil
}

func ValidateRead(path string) (bool, string) {
	if isAutokerenConfigPath(path) {
		return true, "blocked: autokeren config directory"
	}
	lower := normalized(path)
	for _, name := range hardReadNames {
		if strings.Contains(lower, name) {
			return true, "blocked: sensitive file (" + name + ")"
		}
	}
	return false, ""
}

func isAutokerenConfigPath(path string) bool {
	home, err := os.UserHomeDir()
	if err != nil {
		return false
	}
	configRoot := filepath.Join(home, ".config", "autokeren")
	return within(configRoot, path)
}

func NeedsReadPermission(path string) (bool, string) {
	lower := normalized(path)
	for _, name := range softReadNames {
		if strings.Contains(lower, name) {
			return true, "sensitive file (" + name + ") — perlu izin"
		}
	}
	return false, ""
}

func ValidateWriteTarget(path string) error {
	lower := normalized(path)
	for _, name := range writeNames {
		if strings.Contains(lower, name) {
			return fmt.Errorf("blocked: sensitive write target (%s)", name)
		}
	}
	return nil
}

func DangerousCommand(command string) (bool, string) {
	for _, item := range dangerous {
		if regexp.MustCompile(item.expression).MatchString(command) {
			return true, "blocked: " + item.reason
		}
	}
	return false, ""
}

func (g *Guard) Validate(relativePath, content string) ([]string, error) {
	if g == nil {
		return nil, nil
	}
	warnings := make([]string, 0)
	if g.policy.GuardianEnabled {
		duplicates := g.duplicateFunctions(relativePath, content)
		if len(duplicates) > 0 {
			message := "Architecture Guardian: fungsi duplikat " + strings.Join(duplicates, ", ")
			if g.policy.BlockDuplicates {
				return nil, errors.New(message)
			}
			warnings = append(warnings, message)
		}
	}
	if g.policy.EnforcementEnabled {
		ruleWarnings, ruleError := g.enforce(relativePath, content)
		warnings = append(warnings, ruleWarnings...)
		if ruleError != nil {
			return warnings, ruleError
		}
	}
	if g.policy.SecurityEnabled && g.policy.ScanOnWrite {
		findings := Scan(relativePath, content, g.policy.Checks)
		for _, finding := range findings {
			if finding.Severity == "CRITICAL" && g.policy.BlockOnCritical {
				return warnings, errors.New("Vibe-Security blocked: " + finding.Description)
			}
			warnings = append(warnings, "Security "+finding.Severity+": "+finding.Description)
		}
	}
	return warnings, nil
}

type Finding struct {
	Severity    string
	Description string
}

func Scan(filePath, content string, checks []string) []Finding {
	enabled := map[string]bool{}
	for _, check := range checks {
		enabled[check] = true
	}
	if len(enabled) == 0 {
		for _, check := range []string{"secrets", "sqli", "xss", "forbidden"} {
			enabled[check] = true
		}
	}
	findings := make([]Finding, 0)
	if enabled["secrets"] && !strings.HasSuffix(filePath, ".env.example") && !strings.HasSuffix(filePath, ".env.sample") {
		for _, item := range secretPatterns {
			if regexp.MustCompile(item.expression).MatchString(content) {
				findings = append(findings, Finding{Severity: "CRITICAL", Description: item.reason})
			}
		}
	}
	code := isCodeFile(filePath)
	if enabled["sqli"] && code && (regexp.MustCompile(`(?is)(?:SELECT|INSERT|UPDATE|DELETE|WHERE).*['"]\s*\+\s*\w`).MatchString(content) || regexp.MustCompile(`(?is)f['"].*(?:SELECT|INSERT|UPDATE|DELETE|WHERE).*\{`).MatchString(content) || regexp.MustCompile(`(?is)\.format\(.*(?:SELECT|INSERT|UPDATE|DELETE|WHERE)`).MatchString(content)) {
		findings = append(findings, Finding{Severity: "HIGH", Description: "SQL query dengan string interpolation"})
	}
	if enabled["xss"] && (strings.Contains(content, "dangerouslySetInnerHTML") || strings.Contains(content, ".innerHTML =") || strings.Contains(content, "document.write(") || strings.Contains(content, "v-html")) {
		findings = append(findings, Finding{Severity: "MEDIUM", Description: "pola XSS terdeteksi"})
	}
	if enabled["forbidden"] && code && (regexp.MustCompile(`\beval\s*\(`).MatchString(content) || regexp.MustCompile(`\bFunction\s*\(`).MatchString(content) || regexp.MustCompile(`\bset(?:Timeout|Interval)\s*\(\s*["']`).MatchString(content)) {
		findings = append(findings, Finding{Severity: "HIGH", Description: "kode dinamis berbahaya terdeteksi"})
	}
	return findings
}

func (g *Guard) duplicateFunctions(relativePath, content string) []string {
	newNames := functionNames(content)
	if len(newNames) == 0 {
		return nil
	}
	g.mu.Lock()
	defer g.mu.Unlock()
	if !g.scanned || g.writesScanned >= g.policy.ScanInterval {
		g.functionIndex = g.scanFunctionIndex()
		g.scanned = true
		g.writesScanned = 0
	}
	relativePath = filepath.Clean(relativePath)
	duplicates := make([]string, 0)
	seen := map[string]struct{}{}
	for _, name := range newNames {
		for _, existingPath := range g.functionIndex[name] {
			if existingPath == relativePath {
				continue
			}
			if _, found := seen[name]; !found {
				seen[name] = struct{}{}
				duplicates = append(duplicates, name)
			}
			break
		}
	}
	return duplicates
}

func (g *Guard) RecordWrite(relativePath, content string) {
	if g == nil || !g.policy.GuardianEnabled {
		return
	}
	g.mu.Lock()
	defer g.mu.Unlock()
	if !g.scanned {
		return
	}
	relativePath = filepath.Clean(relativePath)
	for name, paths := range g.functionIndex {
		kept := paths[:0]
		for _, path := range paths {
			if path != relativePath {
				kept = append(kept, path)
			}
		}
		if len(kept) == 0 {
			delete(g.functionIndex, name)
			continue
		}
		g.functionIndex[name] = kept
	}
	for _, name := range functionNames(content) {
		g.functionIndex[name] = append(g.functionIndex[name], relativePath)
	}
	g.writesScanned++
}

func (g *Guard) scanFunctionIndex() map[string][]string {
	index := map[string][]string{}
	_ = filepath.Walk(g.root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if info.IsDir() {
			if ignoredDirectory(info.Name()) && path != g.root {
				return filepath.SkipDir
			}
			return nil
		}
		if !isCodeFile(path) {
			return nil
		}
		relativePath, relErr := filepath.Rel(g.root, path)
		if relErr != nil {
			return nil
		}
		data, readErr := os.ReadFile(path)
		if readErr != nil {
			return nil
		}
		for _, name := range functionNames(string(data)) {
			index[name] = append(index[name], filepath.Clean(relativePath))
		}
		return nil
	})
	return index
}

func ignoredDirectory(name string) bool {
	switch name {
	case ".git", ".hg", ".svn", ".venv", "venv", "env", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "node_modules", ".next", ".nuxt", ".turbo", "build", "dist", ".eggs", ".tox", "htmlcov", ".idea", ".vscode", ".ak-checkpoints", ".ak-sessions", ".autokeren":
		return true
	default:
		return strings.HasSuffix(name, ".egg-info")
	}
}

func (g *Guard) enforce(filePath, content string) ([]string, error) {
	path := g.policy.RulesFile
	if path == "" {
		path = ".ak-rules.yaml"
	}
	data, err := os.ReadFile(filepath.Join(g.root, path))
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var document struct {
		Rules map[string]struct {
			Action         string   `yaml:"action"`
			Message        string   `yaml:"message"`
			Limit          int      `yaml:"limit"`
			ForbidPatterns []string `yaml:"forbid_patterns"`
			Forbid         []string `yaml:"forbid"`
		} `yaml:"rules"`
	}
	if err := yaml.Unmarshal(data, &document); err != nil {
		return nil, fmt.Errorf("rules file tidak valid: %w", err)
	}
	warnings := make([]string, 0)
	for name, rule := range document.Rules {
		violated := false
		if rule.Limit > 0 && strings.Count(content, "\n")+1 > rule.Limit {
			violated = true
		}
		for _, expression := range rule.ForbidPatterns {
			re, compileErr := regexp.Compile(expression)
			if compileErr != nil {
				return warnings, fmt.Errorf("regex rule %s tidak valid: %w", name, compileErr)
			}
			if re.MatchString(content) {
				violated = true
			}
		}
		for _, value := range rule.Forbid {
			if strings.Contains(content, value) {
				violated = true
			}
		}
		if !violated {
			continue
		}
		message := rule.Message
		if message == "" {
			message = "aturan dilanggar: " + name
		}
		if rule.Action == "block" && g.policy.BlockOnRuleViolation {
			return warnings, errors.New("Live Enforcement blocked: " + message)
		}
		warnings = append(warnings, "Live Enforcement: "+message)
	}
	return warnings, nil
}

func within(root, target string) bool {
	rel, err := filepath.Rel(root, target)
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}

func resolveTarget(target string) (string, error) {
	current := target
	missing := make([]string, 0)
	for {
		if _, err := os.Lstat(current); err == nil {
			resolved, resolveErr := filepath.EvalSymlinks(current)
			if resolveErr != nil {
				return "", resolveErr
			}
			for index := len(missing) - 1; index >= 0; index-- {
				resolved = filepath.Join(resolved, missing[index])
			}
			return filepath.Clean(resolved), nil
		} else if !os.IsNotExist(err) {
			return "", err
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", errors.New("tidak dapat resolve path")
		}
		missing = append(missing, filepath.Base(current))
		current = parent
	}
}

func normalized(path string) string {
	return strings.ToLower(strings.ReplaceAll(filepath.Clean(path), "\\", "/"))
}

func isCodeFile(path string) bool {
	switch strings.ToLower(filepath.Ext(path)) {
	case ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java":
		return true
	default:
		return false
	}
}

func functionNames(content string) []string {
	pattern := regexp.MustCompile(`(?m)^\s*(?:func|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)|^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)`)
	matches := pattern.FindAllStringSubmatch(content, -1)
	names := make([]string, 0, len(matches))
	for _, match := range matches {
		for _, capture := range match[1:] {
			if capture != "" {
				names = append(names, capture)
				break
			}
		}
	}
	return names
}

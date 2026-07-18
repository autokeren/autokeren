package ghost

import (
	"sort"
	"strings"
)

var mutableTools = map[string]struct{}{
	"browser":         {},
	"cf_build_next":   {},
	"cf_d1":           {},
	"cf_deploy":       {},
	"cf_kv":           {},
	"deploy_project":  {},
	"git_auto_commit": {},
	"git_branch":      {},
	"git_commit":      {},
	"patch_file":      {},
	"run_shell":       {},
	"write_file":      {},
}

func AllowedTools(values []string) []string {
	unique := map[string]struct{}{}
	for _, value := range values {
		name := strings.TrimSpace(value)
		if _, ok := mutableTools[name]; ok {
			unique[name] = struct{}{}
		}
	}
	output := make([]string, 0, len(unique))
	for name := range unique {
		output = append(output, name)
	}
	sort.Strings(output)
	return output
}

func ChildEnvironment(parent []string, allowedTools []string, resultPath string) []string {
	permitted := map[string]struct{}{
		"APPDATA":               {},
		"AUTOKEREN_API_KEY":     {},
		"AK_API_KEY":            {},
		"AUTOKEREN_CONFIG_DIR":  {},
		"COMSPEC":               {},
		"CLOUDFLARE_ACCOUNT_ID": {},
		"CLOUDFLARE_API_KEY":    {},
		"CLOUDFLARE_API_TOKEN":  {},
		"GEMINI_API_KEY":        {},
		"HOME":                  {},
		"HOMEDRIVE":             {},
		"HOMEPATH":              {},
		"HTTP_PROXY":            {},
		"HTTPS_PROXY":           {},
		"LANG":                  {},
		"LC_ALL":                {},
		"LC_CTYPE":              {},
		"LOCALAPPDATA":          {},
		"NO_PROXY":              {},
		"OPENAI_API_KEY":        {},
		"PATH":                  {},
		"PATHEXT":               {},
		"SSL_CERT_FILE":         {},
		"SSL_CERT_DIR":          {},
		"SYSTEMROOT":            {},
		"TEMP":                  {},
		"TMP":                   {},
		"USERPROFILE":           {},
		"WINDIR":                {},
		"XDG_CONFIG_HOME":       {},
	}
	environment := make([]string, 0, len(parent)+2)
	for _, item := range parent {
		key, _, found := strings.Cut(item, "=")
		if found {
			if _, ok := permitted[strings.ToUpper(strings.TrimSpace(key))]; ok {
				environment = append(environment, item)
			}
		}
	}
	environment = append(environment, "AUTOKEREN_GHOST_CHILD=1")
	environment = append(environment, "AUTOKEREN_GHOST_ALLOWED_TOOLS="+strings.Join(AllowedTools(allowedTools), ","))
	if resultPath != "" {
		environment = append(environment, "AUTOKEREN_GHOST_RESULT_PATH="+resultPath)
	}
	return environment
}

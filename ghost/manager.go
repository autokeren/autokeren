package ghost

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"
)

type GhostAgentInfo struct {
	ID           int       `json:"id"`
	Task         string    `json:"task"`
	Role         string    `json:"role,omitempty"`
	AllowedTools []string  `json:"allowed_tools,omitempty"`
	Status       string    `json:"status"`
	StartedAt    time.Time `json:"started_at"`
	FinishedAt   time.Time `json:"finished_at,omitempty"`
	ExitCode     int       `json:"exit_code"`
	PID          int       `json:"pid,omitempty"`
	BinaryPath   string    `json:"binary_path,omitempty"`
	ProcessStart int64     `json:"process_start,omitempty"`
	Error        string    `json:"error,omitempty"`
	LogFile      string    `json:"log_file"`
	ResultFile   string    `json:"result_file,omitempty"`
}

func (info GhostAgentInfo) Runtime() float64 {
	if info.Status == "running" {
		return time.Since(info.StartedAt).Seconds()
	}
	if info.FinishedAt.IsZero() {
		return 0
	}
	return info.FinishedAt.Sub(info.StartedAt).Seconds()
}

type GhostManager struct {
	ProjectRoot string
	MaxAgents   int
	Prefix      string
	Timeout     time.Duration

	mu      sync.RWMutex
	agents  map[int]*GhostAgentInfo
	cancels map[int]context.CancelFunc
	procs   map[int]*exec.Cmd
	nextID  int
}

type SpawnOptions struct {
	Task         string
	Context      string
	Role         string
	ModelID      string
	AllowedTools []string
}

func NewGhostManager(projectRoot string) *GhostManager {
	gm := &GhostManager{
		ProjectRoot: projectRoot,
		MaxAgents:   3,
		Prefix:      "ak-ghost",
		Timeout:     30 * time.Minute,
		agents:      make(map[int]*GhostAgentInfo),
		cancels:     make(map[int]context.CancelFunc),
		procs:       make(map[int]*exec.Cmd),
		nextID:      1,
	}
	gm.loadExisting()
	return gm
}

func (gm *GhostManager) loadExisting() {
	gm.mu.Lock()
	defer gm.mu.Unlock()
	gm.loadExistingLocked()
}

func (gm *GhostManager) loadExistingLocked() {
	entries, err := os.ReadDir(gm.ProjectRoot)
	if err != nil {
		return
	}
	for _, entry := range entries {
		if id, ok := ghostFileID(entry.Name()); ok && id >= gm.nextID {
			gm.nextID = id + 1
		}
		if filepath.Ext(entry.Name()) != ".json" || !strings.HasPrefix(entry.Name(), ".ak-ghost-") {
			continue
		}
		data, err := os.ReadFile(filepath.Join(gm.ProjectRoot, entry.Name()))
		if err != nil {
			continue
		}
		var info GhostAgentInfo
		if json.Unmarshal(data, &info) != nil || info.ID == 0 {
			continue
		}
		// Metadata produced by the legacy Python/tmux manager has no PID. It
		// cannot prove a live Go process and must not reappear as an active ghost.
		if info.PID == 0 {
			continue
		}
		if info.Status == "running" && !processMatches(&info) {
			info.Status = "completed"
			info.Error = "ghost lama tidak dapat diverifikasi sebagai proses Autokeren"
			info.FinishedAt = time.Now()
		}
		gm.agents[info.ID] = &info
	}
}

func ghostFileID(name string) (int, bool) {
	if !strings.HasPrefix(name, ".ak-ghost-") {
		return 0, false
	}
	for _, extension := range []string{".result.json", ".json", ".log"} {
		if strings.HasSuffix(name, extension) {
			value := strings.TrimSuffix(strings.TrimPrefix(name, ".ak-ghost-"), extension)
			id, err := strconv.Atoi(value)
			return id, err == nil && id > 0
		}
	}
	return 0, false
}

func (gm *GhostManager) Spawn(task string) (*GhostAgentInfo, error) {
	return gm.SpawnWithOptions(SpawnOptions{Task: task})
}

func (gm *GhostManager) SpawnWithOptions(options SpawnOptions) (*GhostAgentInfo, error) {
	task := strings.TrimSpace(options.Task)
	if options.Context != "" {
		task = "Konteks:\n" + options.Context + "\n\nTask:\n" + task
	}
	if options.Role != "" {
		task = "Peran: " + options.Role + "\n\n" + task
	}
	allowedTools := AllowedTools(options.AllowedTools)
	gm.mu.Lock()
	defer gm.mu.Unlock()
	if gm.activeCountLocked() >= gm.MaxAgents {
		return nil, fmt.Errorf("maksimal %d ghost agent aktif", gm.MaxAgents)
	}

	id := gm.nextID
	var logFile string
	var log *os.File
	for {
		logFile = filepath.Join(gm.ProjectRoot, fmt.Sprintf(".ak-ghost-%d.log", id))
		opened, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_EXCL, 0o600)
		if os.IsExist(err) {
			id++
			continue
		}
		if err != nil {
			return nil, fmt.Errorf("gagal membuka log ghost: %w", err)
		}
		log = opened
		break
	}
	gm.nextID = id + 1
	resultFile := filepath.Join(gm.ProjectRoot, fmt.Sprintf(".ak-ghost-%d.result.json", id))

	binary := gm.binaryPath()
	ctx, cancel := context.WithTimeout(context.Background(), gm.Timeout)
	args := []string{"--engine", "go", "--non-interactive", "--task", task}
	if options.ModelID != "" {
		args = append(args, "--model", options.ModelID)
	}
	cmd := exec.CommandContext(ctx, binary, args...)
	cmd.Dir = gm.ProjectRoot
	cmd.Env = ChildEnvironment(os.Environ(), allowedTools, resultFile)
	configureProcessGroup(cmd)
	cmd.Stdout = log
	cmd.Stderr = log
	if err := cmd.Start(); err != nil {
		cancel()
		_ = log.Close()
		_ = os.Remove(logFile)
		return nil, fmt.Errorf("gagal memulai ghost: %w", err)
	}

	info := &GhostAgentInfo{ID: id, Task: task, Role: options.Role, AllowedTools: allowedTools, Status: "running", StartedAt: time.Now(), LogFile: logFile, ResultFile: resultFile, PID: cmd.Process.Pid}
	if identity, ok := readProcessIdentity(cmd.Process.Pid); ok {
		info.BinaryPath = identity.Executable
		info.ProcessStart = identity.StartedAt
	}
	gm.agents[id] = info
	gm.cancels[id] = cancel
	gm.procs[id] = cmd
	gm.writeMetadataLocked(info)
	go gm.wait(id, cmd, ctx, log)
	return info, nil
}

func (gm *GhostManager) SpawnSync(ctx context.Context, options SpawnOptions) (string, error) {
	task := strings.TrimSpace(options.Task)
	if options.Context != "" {
		task = "Konteks:\n" + options.Context + "\n\nTask:\n" + task
	}
	if options.Role != "" {
		task = "Peran: " + options.Role + "\n\n" + task
	}
	args := []string{"--engine", "go", "--non-interactive", "--task", task}
	if options.ModelID != "" {
		args = append(args, "--model", options.ModelID)
	}
	childCtx, cancel := context.WithTimeout(ctx, gm.Timeout)
	defer cancel()
	cmd := exec.CommandContext(childCtx, gm.binaryPath(), args...)
	cmd.Dir = gm.ProjectRoot
	cmd.Env = ChildEnvironment(os.Environ(), options.AllowedTools, "")
	configureProcessGroup(cmd)
	out, err := cmd.CombinedOutput()
	if childCtx.Err() != nil {
		return string(out), childCtx.Err()
	}
	if err != nil {
		return string(out), fmt.Errorf("ghost sync gagal: %w", err)
	}
	return string(out), nil
}

func (gm *GhostManager) binaryPath() string {
	if binary := os.Getenv("AUTOKEREN_GHOST_BIN"); binary != "" {
		return resolveBinaryPath(binary, runtime.GOOS == "windows")
	}
	for _, candidate := range []string{"./autokeren-cli", "./ak"} {
		path := resolveBinaryPath(filepath.Join(gm.ProjectRoot, candidate), runtime.GOOS == "windows")
		if _, err := os.Stat(path); err == nil {
			return path
		}
	}
	if executable, err := os.Executable(); err == nil {
		return executable
	}
	return "autokeren"
}

func resolveBinaryPath(path string, windows bool) string {
	if !windows || filepath.Ext(path) != "" {
		return path
	}
	if _, err := os.Stat(path + ".exe"); err == nil {
		return path + ".exe"
	}
	return path
}

func (gm *GhostManager) wait(id int, cmd *exec.Cmd, ctx context.Context, log *os.File) {
	err := cmd.Wait()
	_ = log.Close()
	gm.mu.Lock()
	defer gm.mu.Unlock()
	info, ok := gm.agents[id]
	if !ok {
		return
	}
	if info.Status == "killed" {
		info.FinishedAt = time.Now()
	} else if ctx.Err() == context.DeadlineExceeded {
		info.Status = "timeout"
		info.Error = ctx.Err().Error()
		info.FinishedAt = time.Now()
	} else if err != nil {
		info.Status = "failed"
		info.Error = err.Error()
		info.FinishedAt = time.Now()
	} else {
		info.Status = "completed"
		info.FinishedAt = time.Now()
	}
	if cmd.ProcessState != nil {
		info.ExitCode = cmd.ProcessState.ExitCode()
	}
	delete(gm.cancels, id)
	delete(gm.procs, id)
	gm.writeMetadataLocked(info)
}

func (gm *GhostManager) activeCountLocked() int {
	count := 0
	for _, info := range gm.agents {
		if info.Status == "running" {
			count++
		}
	}
	return count
}

func (gm *GhostManager) CheckStatus(agentID int) string {
	gm.mu.RLock()
	defer gm.mu.RUnlock()
	if info, ok := gm.agents[agentID]; ok {
		return info.Status
	}
	return "unknown"
}

func (gm *GhostManager) Kill(agentID int) bool {
	gm.mu.Lock()
	info, ok := gm.agents[agentID]
	cancel, hasCancel := gm.cancels[agentID]
	if !ok || info.Status != "running" {
		gm.mu.Unlock()
		return false
	}
	if cmd, ok := gm.procs[agentID]; ok {
		info.Status = "killed"
		if hasCancel {
			cancel()
		}
		terminateProcessGroup(cmd)
	} else if info.PID > 0 && processMatches(info) {
		info.Status = "killed"
		terminatePID(info.PID)
	} else {
		info.Status = "completed"
		info.Error = "ghost tidak dihentikan karena identitas proses tidak dapat diverifikasi"
		info.FinishedAt = time.Now()
		gm.writeMetadataLocked(info)
		gm.mu.Unlock()
		return false
	}
	gm.writeMetadataLocked(info)
	gm.mu.Unlock()
	return true
}

func (gm *GhostManager) List() []*GhostAgentInfo {
	gm.mu.RLock()
	defer gm.mu.RUnlock()
	list := make([]*GhostAgentInfo, 0, len(gm.agents))
	for _, info := range gm.agents {
		copyInfo := *info
		list = append(list, &copyInfo)
	}
	return list
}

func (gm *GhostManager) ActiveList() []*GhostAgentInfo {
	gm.mu.RLock()
	defer gm.mu.RUnlock()
	list := make([]*GhostAgentInfo, 0)
	for _, info := range gm.agents {
		if info.Status != "running" {
			continue
		}
		copyInfo := *info
		list = append(list, &copyInfo)
	}
	return list
}

func (gm *GhostManager) AvailableCapacity() int {
	gm.mu.RLock()
	defer gm.mu.RUnlock()
	available := gm.MaxAgents - gm.activeCountLocked()
	if available < 0 {
		return 0
	}
	return available
}

func (gm *GhostManager) Refresh() {
	gm.mu.Lock()
	defer gm.mu.Unlock()
	gm.loadExistingLocked()
	for _, info := range gm.agents {
		if info.Status == "running" && !gm.ownsRunningProcessLocked(info) {
			info.Status = "completed"
			info.FinishedAt = time.Now()
			info.Error = "ghost tidak lagi dapat diverifikasi sebagai proses Autokeren"
			gm.writeMetadataLocked(info)
		}
	}
}

func (gm *GhostManager) ownsRunningProcessLocked(info *GhostAgentInfo) bool {
	if info == nil || info.PID <= 0 {
		return false
	}
	return processMatches(info)
}

func (gm *GhostManager) GetOutput(agentID int) string {
	gm.mu.RLock()
	info, ok := gm.agents[agentID]
	logFile := ""
	if ok {
		logFile = info.LogFile
	}
	gm.mu.RUnlock()
	if !ok || logFile == "" {
		return ""
	}
	data, err := os.ReadFile(logFile)
	if err != nil {
		return ""
	}
	if len(data) > 50000 {
		data = data[len(data)-50000:]
	}
	return string(data)
}

func (gm *GhostManager) writeMetadataLocked(info *GhostAgentInfo) {
	path := filepath.Join(gm.ProjectRoot, fmt.Sprintf(".ak-ghost-%d.json", info.ID))
	data, err := json.Marshal(info)
	if err != nil {
		return
	}
	_ = os.WriteFile(path, data, 0o600)
}

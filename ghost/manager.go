package ghost

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"
)

type GhostAgentInfo struct {
	ID         int       `json:"id"`
	Task       string    `json:"task"`
	Status     string    `json:"status"`
	StartedAt  time.Time `json:"started_at"`
	FinishedAt time.Time `json:"finished_at,omitempty"`
	ExitCode   int       `json:"exit_code"`
	Error      string    `json:"error,omitempty"`
	LogFile    string    `json:"log_file"`
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
	nextID  int
}

func NewGhostManager(projectRoot string) *GhostManager {
	return &GhostManager{
		ProjectRoot: projectRoot,
		MaxAgents:   3,
		Prefix:      "ak-ghost",
		Timeout:     30 * time.Minute,
		agents:      make(map[int]*GhostAgentInfo),
		cancels:     make(map[int]context.CancelFunc),
		nextID:      1,
	}
}

func (gm *GhostManager) Spawn(task string) (*GhostAgentInfo, error) {
	gm.mu.Lock()
	defer gm.mu.Unlock()
	if gm.activeCountLocked() >= gm.MaxAgents {
		return nil, fmt.Errorf("maksimal %d ghost agent aktif", gm.MaxAgents)
	}

	id := gm.nextID
	gm.nextID++
	logFile := filepath.Join(gm.ProjectRoot, fmt.Sprintf(".ak-ghost-%d.log", id))
	log, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o600)
	if err != nil {
		return nil, fmt.Errorf("gagal membuka log ghost: %w", err)
	}

	binary := os.Getenv("AUTOKEREN_GHOST_BIN")
	if binary == "" {
		for _, candidate := range []string{"./autokeren-cli", "./ak", "autokeren"} {
			if candidate == "autokeren" {
				binary = candidate
				break
			}
			if _, statErr := os.Stat(filepath.Join(gm.ProjectRoot, candidate)); statErr == nil {
				binary = candidate
				break
			}
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), gm.Timeout)
	cmd := exec.CommandContext(ctx, binary, "--engine", "go", "--non-interactive", "--task", task)
	cmd.Dir = gm.ProjectRoot
	configureProcessGroup(cmd)
	cmd.Stdout = log
	cmd.Stderr = log
	if err := cmd.Start(); err != nil {
		cancel()
		_ = log.Close()
		return nil, fmt.Errorf("gagal memulai ghost: %w", err)
	}

	info := &GhostAgentInfo{ID: id, Task: task, Status: "running", StartedAt: time.Now(), LogFile: logFile}
	gm.agents[id] = info
	gm.cancels[id] = cancel
	gm.writeMetadataLocked(info)
	go gm.wait(id, cmd, ctx, log)
	return info, nil
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
	info.Status = "killed"
	if hasCancel {
		cancel()
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

func (gm *GhostManager) GetOutput(agentID int) string {
	gm.mu.RLock()
	info, ok := gm.agents[agentID]
	gm.mu.RUnlock()
	if !ok || info.LogFile == "" {
		return ""
	}
	data, err := os.ReadFile(info.LogFile)
	if err != nil {
		return ""
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

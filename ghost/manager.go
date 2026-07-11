package ghost

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

type GhostAgentInfo struct {
	ID        int       `json:"id"`
	Task      string    `json:"task"`
	Status    string    `json:"status"`
	StartedAt time.Time `json:"started_at"`
	LogFile   string    `json:"log_file"`
}

func (info GhostAgentInfo) Runtime() float64 {
	if info.Status == "running" {
		return time.Since(info.StartedAt).Seconds()
	}
	return 0.0
}

type GhostManager struct {
	ProjectRoot string
	MaxAgents   int
	Prefix      string
	agents      map[int]*GhostAgentInfo
	nextID      int
}

func NewGhostManager(projectRoot string) *GhostManager {
	return &GhostManager{
		ProjectRoot: projectRoot,
		MaxAgents:   3,
		Prefix:      "ak-ghost",
		agents:      make(map[int]*GhostAgentInfo),
		nextID:      1,
	}
}

func (gm *GhostManager) Spawn(task string) (*GhostAgentInfo, error) {
	if len(gm.agents) >= gm.MaxAgents {
		return nil, fmt.Errorf("maksimal %d ghost agent aktif", gm.MaxAgents)
	}

	agentID := gm.nextID
	gm.nextID++

	sessionName := fmt.Sprintf("%s-%d", gm.Prefix, agentID)
	logFile := filepath.Join(gm.ProjectRoot, fmt.Sprintf(".ak-ghost-%d.log", agentID))

	info := &GhostAgentInfo{
		ID:        agentID,
		Task:      task,
		Status:    "running",
		StartedAt: time.Now(),
		LogFile:   logFile,
	}

	// 1. Cek apakah tmux terpasang
	_, err := exec.LookPath("tmux")
	if err != nil {
		return nil, fmt.Errorf("tmux tidak ditemukan di sistem. Harap pasang tmux terlebih dahulu")
	}

	// 2. Buat tmux session baru di background
	cmdNew := exec.Command("tmux", "new-session", "-d", "-s", sessionName, "-c", gm.ProjectRoot)
	if err := cmdNew.Run(); err != nil {
		return nil, fmt.Errorf("gagal membuat tmux session: %v", err)
	}

	// 3. Jalankan autokeren-cli (biner Go baru kita) untuk memproses task
	// Gunakan full path biner jika berjalan di folder lokal, atau default global "autokeren"
	binPath := "./autokeren-cli"
	if _, err := os.Stat(binPath); os.IsNotExist(err) {
		binPath = "autokeren"
	}

	cmdStr := fmt.Sprintf("%s --non-interactive --task %q 2>&1 | tee %s", binPath, task, logFile)
	cmdSend := exec.Command("tmux", "send-keys", "-t", sessionName, cmdStr, "Enter")
	if err := cmdSend.Run(); err != nil {
		gm.Kill(agentID)
		return nil, fmt.Errorf("gagal mengirimkan perintah ke tmux: %v", err)
	}

	gm.agents[agentID] = info
	return info, nil
}

func (gm *GhostManager) CheckStatus(agentID int) string {
	info, exists := gm.agents[agentID]
	if !exists {
		return "unknown"
	}

	sessionName := fmt.Sprintf("%s-%d", gm.Prefix, agentID)
	cmd := exec.Command("tmux", "has-session", "-t", sessionName)
	err := cmd.Run()
	
	// Jika tmux has-session mengembalikan error (exit code != 0), session tmux sudah mati
	if err != nil {
		info.Status = "completed"
	}
	return info.Status
}

func (gm *GhostManager) Kill(agentID int) bool {
	info, exists := gm.agents[agentID]
	if !exists {
		return false
	}

	sessionName := fmt.Sprintf("%s-%d", gm.Prefix, agentID)
	cmd := exec.Command("tmux", "kill-session", "-t", sessionName)
	_ = cmd.Run()

	info.Status = "killed"
	return true
}

func (gm *GhostManager) List() []*GhostAgentInfo {
	list := make([]*GhostAgentInfo, 0, len(gm.agents))
	for _, a := range gm.agents {
		gm.CheckStatus(a.ID)
		list = append(list, a)
	}
	return list
}

func (gm *GhostManager) GetOutput(agentID int) string {
	info, exists := gm.agents[agentID]
	if !exists || info.LogFile == "" {
		return ""
	}

	data, err := os.ReadFile(info.LogFile)
	if err != nil {
		return ""
	}
	return string(data)
}

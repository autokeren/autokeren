package project

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/autokeren/autokeren/ghost"
)

type Worker struct {
	Name        string    `json:"name"`
	Task        string    `json:"task"`
	Status      string    `json:"status"`
	DependsOn   []string  `json:"depends_on,omitempty"`
	Attempts    int       `json:"attempts"`
	MaxAttempts int       `json:"max_attempts"`
	Output      string    `json:"output,omitempty"`
	Error       string    `json:"error,omitempty"`
	GhostID     int       `json:"ghost_id,omitempty"`
	StartedAt   time.Time `json:"started_at,omitempty"`
	FinishedAt  time.Time `json:"finished_at,omitempty"`
}

type Project struct {
	Name             string    `json:"name"`
	Workers          []*Worker `json:"workers"`
	SchedulerEnabled bool      `json:"scheduler_enabled"`
	CreatedAt        time.Time `json:"created_at"`
}

type Manager struct {
	mu       sync.RWMutex
	projects map[string]*Project
	active   string
	path     string
}

type persistedState struct {
	Active   string              `json:"active"`
	Projects map[string]*Project `json:"projects"`
}

type Schedule struct {
	Launched int
	Queued   int
	Blocked  int
	Capacity int
}

func NewManager() *Manager {
	return &Manager{projects: make(map[string]*Project)}
}

func NewPersistentManager(projectRoot string) (*Manager, error) {
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return nil, fmt.Errorf("resolve project root: %w", err)
	}
	manager := NewManager()
	manager.path = filepath.Join(root, ".autokeren", "projects.json")
	data, err := os.ReadFile(manager.path)
	if os.IsNotExist(err) {
		return manager, nil
	}
	if err != nil {
		return nil, fmt.Errorf("baca project state: %w", err)
	}
	var state persistedState
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, fmt.Errorf("baca project state tidak valid: %w", err)
	}
	if state.Projects != nil {
		manager.projects = state.Projects
		for _, project := range manager.projects {
			for _, worker := range project.Workers {
				if worker.MaxAttempts < 1 {
					worker.MaxAttempts = 2
				}
			}
		}
	}
	manager.active = state.Active
	return manager, nil
}

func (m *Manager) New(name string) (*Project, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		return nil, fmt.Errorf("nama project kosong")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, exists := m.projects[name]; exists {
		return nil, fmt.Errorf("project %q sudah ada", name)
	}
	project := &Project{Name: name, CreatedAt: time.Now()}
	m.projects[name] = project
	m.active = name
	if err := m.persistLocked(); err != nil {
		return nil, err
	}
	return projectCopy(project), nil
}

func (m *Manager) AddWorker(name, task string) (*Worker, error) {
	name = strings.TrimSpace(name)
	task = strings.TrimSpace(task)
	if name == "" || task == "" {
		return nil, fmt.Errorf("nama agent dan task wajib")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	project := m.projects[m.active]
	if project == nil {
		return nil, fmt.Errorf("belum ada project aktif")
	}
	for _, worker := range project.Workers {
		if worker.Name == name {
			return nil, fmt.Errorf("agent %q sudah ada", name)
		}
	}
	worker := &Worker{Name: name, Task: task, Status: "pending", MaxAttempts: 2}
	project.Workers = append(project.Workers, worker)
	if err := m.persistLocked(); err != nil {
		return nil, err
	}
	return workerCopy(worker), nil
}

func (m *Manager) Active() *Project {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return projectCopy(m.projects[m.active])
}

func (m *Manager) Switch(name string) (*Project, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, exists := m.projects[name]; !exists {
		return nil, fmt.Errorf("project %q tidak ditemukan", name)
	}
	m.active = name
	if err := m.persistLocked(); err != nil {
		return nil, err
	}
	return projectCopy(m.projects[name]), nil
}

func (m *Manager) List() []*Project {
	m.mu.RLock()
	defer m.mu.RUnlock()
	projects := make([]*Project, 0, len(m.projects))
	for _, project := range m.projects {
		projects = append(projects, projectCopy(project))
	}
	return projects
}

func (m *Manager) ActiveName() string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.active
}

func (m *Manager) SetDependencies(name string, dependencies []string) (*Worker, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	project := m.projects[m.active]
	if project == nil {
		return nil, fmt.Errorf("belum ada project aktif")
	}
	worker := project.worker(name)
	if worker == nil {
		return nil, fmt.Errorf("agent %q tidak ditemukan", name)
	}
	clean := uniqueNames(dependencies)
	for _, dependency := range clean {
		if dependency == name || project.worker(dependency) == nil {
			return nil, fmt.Errorf("dependency %q tidak valid", dependency)
		}
	}
	previous := worker.DependsOn
	worker.DependsOn = clean
	if project.hasCycle() {
		worker.DependsOn = previous
		return nil, fmt.Errorf("dependency membuat siklus DAG")
	}
	if err := m.persistLocked(); err != nil {
		return nil, err
	}
	return workerCopy(worker), nil
}

func (m *Manager) Retry(name string) (*Worker, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	project := m.projects[m.active]
	if project == nil {
		return nil, fmt.Errorf("belum ada project aktif")
	}
	worker := project.worker(name)
	if worker == nil || worker.Status != "error" {
		return nil, fmt.Errorf("agent %q tidak dalam status error", name)
	}
	if worker.Attempts >= worker.MaxAttempts {
		return nil, fmt.Errorf("batas retry agent %q sudah tercapai (%d)", name, worker.MaxAttempts)
	}
	worker.Status, worker.Error, worker.GhostID, worker.FinishedAt = "pending", "", 0, time.Time{}
	if err := m.persistLocked(); err != nil {
		return nil, err
	}
	return workerCopy(worker), nil
}

func (m *Manager) Run(ghosts *ghost.GhostManager) (Schedule, error) {
	if err := m.Refresh(ghosts); err != nil {
		return Schedule{}, err
	}
	return m.schedule(ghosts, true)
}

func (m *Manager) Tick(ghosts *ghost.GhostManager) (Schedule, error) {
	if ghosts == nil {
		return Schedule{}, nil
	}
	m.mu.RLock()
	hasActiveProject := m.projects[m.active] != nil
	m.mu.RUnlock()
	if !hasActiveProject {
		return Schedule{Capacity: ghosts.AvailableCapacity()}, nil
	}
	if err := m.Refresh(ghosts); err != nil {
		return Schedule{}, err
	}
	return m.schedule(ghosts, false)
}

func (m *Manager) Pause() (*Project, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	project := m.projects[m.active]
	if project == nil {
		return nil, fmt.Errorf("belum ada project aktif")
	}
	project.SchedulerEnabled = false
	if err := m.persistLocked(); err != nil {
		return nil, err
	}
	return projectCopy(project), nil
}

func (m *Manager) schedule(ghosts *ghost.GhostManager, enable bool) (Schedule, error) {
	if ghosts == nil {
		return Schedule{}, fmt.Errorf("ghost manager tidak tersedia")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	project := m.projects[m.active]
	if project == nil {
		return Schedule{}, fmt.Errorf("belum ada project aktif")
	}
	schedule := Schedule{Capacity: ghosts.AvailableCapacity()}
	if enable {
		project.SchedulerEnabled = true
	}
	if !project.SchedulerEnabled {
		return schedule, nil
	}
	for _, worker := range project.Workers {
		if worker.Status == "blocked" && strings.HasPrefix(worker.Error, "menunggu dependency gagal:") {
			worker.Status, worker.Error = "pending", ""
		}
		if worker.Status != "pending" {
			continue
		}
		ready, blockedBy := project.ready(worker)
		if blockedBy != "" {
			worker.Status, worker.Error = "blocked", "menunggu dependency gagal: "+blockedBy
			schedule.Blocked++
			continue
		}
		if !ready || schedule.Launched >= schedule.Capacity {
			schedule.Queued++
			continue
		}
		if worker.MaxAttempts < 1 {
			worker.MaxAttempts = 2
		}
		if worker.Attempts >= worker.MaxAttempts {
			worker.Status = "error"
			worker.Error = fmt.Sprintf("batas retry tercapai (%d)", worker.MaxAttempts)
			worker.FinishedAt = time.Now()
			continue
		}
		worker.Attempts++
		info, err := ghosts.SpawnWithOptions(ghost.SpawnOptions{Task: worker.Task, Role: worker.Name, Context: "Project: " + project.Name})
		if err != nil {
			worker.Status = "error"
			worker.Error = err.Error()
			worker.FinishedAt = time.Now()
			continue
		}
		worker.GhostID = info.ID
		worker.Status = "running"
		worker.StartedAt = time.Now()
		schedule.Launched++
	}
	if err := m.persistLocked(); err != nil {
		return Schedule{}, err
	}
	return schedule, nil
}

func (m *Manager) Refresh(ghosts *ghost.GhostManager) error {
	if ghosts == nil {
		return nil
	}
	ghosts.Refresh()
	m.mu.Lock()
	defer m.mu.Unlock()
	changed := false
	for _, project := range m.projects {
		for _, worker := range project.Workers {
			if worker.Status != "running" || worker.GhostID == 0 {
				continue
			}
			status := ghosts.CheckStatus(worker.GhostID)
			if status == "running" || status == "unknown" {
				continue
			}
			worker.FinishedAt = time.Now()
			worker.Output = ghosts.GetOutput(worker.GhostID)
			if status == "completed" {
				worker.Status = "done"
			} else {
				worker.Status = "error"
				worker.Error = status
			}
			changed = true
		}
	}
	if changed {
		return m.persistLocked()
	}
	return nil
}

func (m *Manager) persistLocked() error {
	if m.path == "" {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(m.path), 0o700); err != nil {
		return fmt.Errorf("buat direktori project state: %w", err)
	}
	data, err := json.MarshalIndent(persistedState{Active: m.active, Projects: m.projects}, "", "  ")
	if err != nil {
		return fmt.Errorf("serialisasi project state: %w", err)
	}
	temporary := m.path + ".tmp"
	if err := os.WriteFile(temporary, data, 0o600); err != nil {
		return fmt.Errorf("tulis project state: %w", err)
	}
	if err := os.Rename(temporary, m.path); err != nil {
		return fmt.Errorf("simpan project state: %w", err)
	}
	return nil
}

func (p *Project) Summary() string {
	total, done, running, failed, blocked := len(p.Workers), 0, 0, 0, 0
	for _, worker := range p.Workers {
		switch worker.Status {
		case "done":
			done++
		case "running":
			running++
		case "error":
			failed++
		case "blocked":
			blocked++
		}
	}
	return fmt.Sprintf("%d workers — selesai:%d berjalan:%d error:%d blocked:%d", total, done, running, failed, blocked)
}

func (p *Project) Worker(name string) *Worker {
	for _, worker := range p.Workers {
		if worker.Name == name {
			return workerCopy(worker)
		}
	}
	return nil
}

func (p *Project) worker(name string) *Worker {
	for _, worker := range p.Workers {
		if worker.Name == name {
			return worker
		}
	}
	return nil
}

func (p *Project) ready(worker *Worker) (bool, string) {
	for _, dependency := range worker.DependsOn {
		candidate := p.worker(dependency)
		if candidate == nil {
			return false, dependency
		}
		if candidate.Status == "error" || candidate.Status == "blocked" {
			return false, dependency
		}
		if candidate.Status != "done" {
			return false, ""
		}
	}
	return true, ""
}

func (p *Project) hasCycle() bool {
	visiting, visited := map[string]bool{}, map[string]bool{}
	var visit func(string) bool
	visit = func(name string) bool {
		if visiting[name] {
			return true
		}
		if visited[name] {
			return false
		}
		visiting[name] = true
		worker := p.worker(name)
		if worker != nil {
			for _, dependency := range worker.DependsOn {
				if visit(dependency) {
					return true
				}
			}
		}
		visiting[name], visited[name] = false, true
		return false
	}
	for _, worker := range p.Workers {
		if visit(worker.Name) {
			return true
		}
	}
	return false
}

func uniqueNames(values []string) []string {
	seen := map[string]struct{}{}
	output := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" {
			if _, ok := seen[value]; !ok {
				seen[value] = struct{}{}
				output = append(output, value)
			}
		}
	}
	return output
}

func projectCopy(project *Project) *Project {
	if project == nil {
		return nil
	}
	copyProject := *project
	copyProject.Workers = make([]*Worker, 0, len(project.Workers))
	for _, worker := range project.Workers {
		copyProject.Workers = append(copyProject.Workers, workerCopy(worker))
	}
	return &copyProject
}

func workerCopy(worker *Worker) *Worker {
	if worker == nil {
		return nil
	}
	copyWorker := *worker
	return &copyWorker
}

package project

import (
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/autokeren/autokeren/ghost"
)

type Worker struct {
	Name       string
	Task       string
	Status     string
	Output     string
	Error      string
	GhostID    int
	StartedAt  time.Time
	FinishedAt time.Time
}

type Project struct {
	Name      string
	Workers   []*Worker
	CreatedAt time.Time
}

type Manager struct {
	mu       sync.RWMutex
	projects map[string]*Project
	active   string
}

func NewManager() *Manager {
	return &Manager{projects: make(map[string]*Project)}
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
	worker := &Worker{Name: name, Task: task, Status: "pending"}
	project.Workers = append(project.Workers, worker)
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

func (m *Manager) Run(ghosts *ghost.GhostManager) (int, error) {
	if ghosts == nil {
		return 0, fmt.Errorf("ghost manager tidak tersedia")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	project := m.projects[m.active]
	if project == nil {
		return 0, fmt.Errorf("belum ada project aktif")
	}
	launched := 0
	for _, worker := range project.Workers {
		if worker.Status != "pending" {
			continue
		}
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
		launched++
	}
	if launched == 0 {
		return 0, fmt.Errorf("tidak ada agent pending untuk dijalankan")
	}
	return launched, nil
}

func (m *Manager) Refresh(ghosts *ghost.GhostManager) {
	if ghosts == nil {
		return
	}
	ghosts.Refresh()
	m.mu.Lock()
	defer m.mu.Unlock()
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
		}
	}
}

func (p *Project) Summary() string {
	total, done, running, failed := len(p.Workers), 0, 0, 0
	for _, worker := range p.Workers {
		switch worker.Status {
		case "done":
			done++
		case "running":
			running++
		case "error":
			failed++
		}
	}
	return fmt.Sprintf("%d workers — selesai:%d berjalan:%d error:%d", total, done, running, failed)
}

func (p *Project) Worker(name string) *Worker {
	for _, worker := range p.Workers {
		if worker.Name == name {
			return workerCopy(worker)
		}
	}
	return nil
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

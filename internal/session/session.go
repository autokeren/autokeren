package session

import (
	"encoding/json"
	"fmt"
	"github.com/autokeren/autokeren/internal/model"
	"os"
	"path/filepath"
	"time"
)

type Data struct {
	ID        string          `json:"id"`
	Name      string          `json:"name,omitempty"`
	CreatedAt time.Time       `json:"created_at"`
	UpdatedAt time.Time       `json:"updated_at"`
	Messages  []model.Message `json:"messages"`
	Usage     model.Usage     `json:"usage,omitempty"`
}

func New(id string, messages []model.Message) Data {
	now := time.Now().UTC()
	return Data{ID: id, CreatedAt: now, UpdatedAt: now, Messages: messages}
}
func Save(path string, data Data) error {
	if path == "" {
		return fmt.Errorf("session path is empty")
	}
	data.UpdatedAt = time.Now().UTC()
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	raw, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, raw, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}
func Load(path string) (Data, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return Data{}, err
	}
	var data Data
	if err := json.Unmarshal(raw, &data); err != nil {
		return Data{}, err
	}
	return data, nil
}

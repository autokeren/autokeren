package memory

import (
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"unicode"
)

const maxContextRunes = 3000

type Store struct {
	root string
}

func New(root string) Store {
	return Store{root: root}
}

func (s Store) Path() string {
	return filepath.Join(s.root, ".autokeren", "memory.md")
}

func (s Store) Append(section, note string) error {
	section = cleanLine(section)
	note = cleanLine(note)
	if section == "" || note == "" {
		return os.ErrInvalid
	}
	path := s.Path()
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	file, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o600)
	if err != nil {
		return err
	}
	defer file.Close()
	_, err = file.WriteString("- [" + section + "] " + note + "\n")
	return err
}

func (s Store) Search(query string, limit int) []string {
	if limit <= 0 {
		return nil
	}
	documents := s.notes()
	if len(documents) == 0 {
		return nil
	}
	queryTokens := tokens(query)
	if len(queryTokens) == 0 {
		return nil
	}
	docTokens := make([][]string, len(documents))
	documentFrequency := map[string]int{}
	for index, document := range documents {
		docTokens[index] = tokens(document)
		seen := map[string]struct{}{}
		for _, token := range docTokens[index] {
			seen[token] = struct{}{}
		}
		for token := range seen {
			documentFrequency[token]++
		}
	}
	queryVector := weighted(queryTokens, documentFrequency, len(documents))
	queryNorm := norm(queryVector)
	if queryNorm == 0 {
		return nil
	}
	type scored struct {
		value float64
		text  string
	}
	results := make([]scored, 0, len(documents))
	for index, document := range documents {
		vector := weighted(docTokens[index], documentFrequency, len(documents))
		score := cosine(queryVector, queryNorm, vector)
		if score <= 0 {
			continue
		}
		score += float64(index+1) / float64(len(documents)+1) * 0.01
		results = append(results, scored{value: score, text: document})
	}
	sort.SliceStable(results, func(left, right int) bool { return results[left].value > results[right].value })
	if len(results) > limit {
		results = results[:limit]
	}
	output := make([]string, 0, len(results))
	for _, result := range results {
		output = append(output, result.text)
	}
	return output
}

func (s Store) Context(query string, limit int) string {
	notes := s.Search(query, limit)
	if len(notes) == 0 {
		return ""
	}
	return limitRunes("Memori proyek relevan:\n"+bulletList(notes), maxContextRunes)
}

func (s Store) notes() []string {
	data, err := os.ReadFile(filepath.Clean(s.Path()))
	if err != nil {
		return nil
	}
	seen := map[string]struct{}{}
	notes := []string{}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "-") {
			continue
		}
		line = strings.TrimSpace(strings.TrimPrefix(line, "-"))
		if line == "" {
			continue
		}
		if _, exists := seen[line]; exists {
			continue
		}
		seen[line] = struct{}{}
		notes = append(notes, line)
	}
	return notes
}

func tokens(value string) []string {
	return strings.FieldsFunc(strings.ToLower(value), func(r rune) bool { return !unicode.IsLetter(r) && !unicode.IsNumber(r) })
}

func weighted(input []string, documentFrequency map[string]int, totalDocuments int) map[string]float64 {
	counts := map[string]int{}
	for _, token := range input {
		counts[token]++
	}
	vector := make(map[string]float64, len(counts))
	for token, count := range counts {
		idf := math.Log(float64(totalDocuments+1)/float64(documentFrequency[token]+1)) + 1
		vector[token] = float64(count) * idf
	}
	return vector
}

func cosine(left map[string]float64, leftNorm float64, right map[string]float64) float64 {
	rightNorm := norm(right)
	if leftNorm == 0 || rightNorm == 0 {
		return 0
	}
	dot := 0.0
	for token, value := range left {
		dot += value * right[token]
	}
	return dot / (leftNorm * rightNorm)
}

func norm(vector map[string]float64) float64 {
	total := 0.0
	for _, value := range vector {
		total += value * value
	}
	return math.Sqrt(total)
}

func bulletList(notes []string) string {
	var builder strings.Builder
	for _, note := range notes {
		builder.WriteString("- ")
		builder.WriteString(note)
		builder.WriteByte('\n')
	}
	return strings.TrimSpace(builder.String())
}

func cleanLine(value string) string {
	return strings.Join(strings.Fields(value), " ")
}

func limitRunes(value string, max int) string {
	runes := []rune(value)
	if len(runes) <= max {
		return value
	}
	return string(runes[:max]) + "\n[Memori dipotong agar context tetap aman]"
}

package tool

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

type Research struct{ Client *http.Client }
type researchItem struct{ Source, Title, URL string }

func (r Research) Definition() Definition {
	return Definition{Name: "research", Description: "Research a topic using public Hacker News and Reddit search APIs.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"query": map[string]any{"type": "string"}, "sources": map[string]any{"type": "array"}, "max_results": map[string]any{"type": "integer"}}, "required": []string{"query"}}}
}
func (r Research) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (r Research) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	q, _ := args["query"].(string)
	if strings.TrimSpace(q) == "" {
		return Result{OK: false, Error: "query wajib"}
	}
	max := 10
	if v, ok := args["max_results"].(float64); ok && v > 0 {
		max = int(v)
	}
	sources := []string{"hackernews", "reddit"}
	if raw, ok := args["sources"].([]any); ok && len(raw) > 0 {
		sources = nil
		for _, v := range raw {
			if x, ok := v.(string); ok {
				sources = append(sources, x)
			}
		}
	}
	client := r.Client
	if client == nil {
		client = &http.Client{Timeout: 20 * time.Second}
	}
	type item struct{ Source, Title, URL string }
	ch := make(chan item, max*2)
	var wg sync.WaitGroup
	for _, source := range sources {
		wg.Add(1)
		go func(src string) {
			defer wg.Done()
			var items []item
			switch src {
			case "hackernews", "hn":
				items = hnSearch(ctx, client, q, max)
			case "reddit":
				items = redditSearch(ctx, client, q, max)
			}
			for _, v := range items {
				select {
				case ch <- v:
				case <-ctx.Done():
					return
				}
			}
		}(source)
	}
	go func() { wg.Wait(); close(ch) }()
	var out []item
	for v := range ch {
		out = append(out, v)
	}
	if len(out) == 0 {
		return Result{OK: true, Output: "Tidak ada hasil riset."}
	}
	text := "Research: " + q + "\n"
	for i, v := range out {
		if i >= max {
			break
		}
		text += fmt.Sprintf("%d. [%s] %s\n   %s\n", i+1, v.Source, v.Title, v.URL)
	}
	return Result{OK: true, Output: text}
}
func hnSearch(ctx context.Context, c *http.Client, q string, max int) []struct{ Source, Title, URL string } {
	endpoint := "https://hn.algolia.com/api/v1/search?query=" + url.QueryEscape(q) + "&hitsPerPage=" + fmt.Sprint(max)
	var data struct {
		Hits []struct {
			Title, URL string
			StoryTitle string `json:"story_title"`
			StoryURL   string `json:"story_url"`
		} `json:"hits"`
	}
	if !getJSON(ctx, c, endpoint, &data) {
		return nil
	}
	out := make([]struct{ Source, Title, URL string }, 0)
	for _, h := range data.Hits {
		title := h.Title
		if title == "" {
			title = h.StoryTitle
		}
		link := h.URL
		if link == "" {
			link = h.StoryURL
		}
		out = append(out, struct{ Source, Title, URL string }{"hackernews", title, link})
	}
	return out
}
func redditSearch(ctx context.Context, c *http.Client, q string, max int) []struct{ Source, Title, URL string } {
	endpoint := "https://www.reddit.com/search.json?q=" + url.QueryEscape(q) + "&limit=" + fmt.Sprint(max)
	var data struct {
		Data struct {
			Children []struct {
				Data struct{ Title, URL string } `json:"data"`
			} `json:"children"`
		} `json:"data"`
	}
	if !getJSON(ctx, c, endpoint, &data) {
		return nil
	}
	out := make([]struct{ Source, Title, URL string }, 0)
	for _, h := range data.Data.Children {
		out = append(out, struct{ Source, Title, URL string }{"reddit", h.Data.Title, h.Data.URL})
	}
	return out
}
func getJSON(ctx context.Context, c *http.Client, endpoint string, out any) bool {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return false
	}
	req.Header.Set("User-Agent", "autokeren-go-research/1.0")
	resp, err := c.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == 200 && json.NewDecoder(resp.Body).Decode(out) == nil
}

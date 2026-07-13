package ipc

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

// JSONRPCMessage mewakili request, response, atau notification JSON-RPC 2.0
type JSONRPCMessage struct {
	JSONRPC string          `json:"jsonrpc"`
	Method  string          `json:"method,omitempty"`
	Params  json.RawMessage `json:"params,omitempty"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *JSONRPCError   `json:"error,omitempty"`
	ID      interface{}     `json:"id,omitempty"`
}

type JSONRPCError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// IPCCallbacks mewakili callback dari daemon untuk merespon turn atau event
type IPCCallbacks struct {
	OnModelStart      func()
	OnModelEnd        func(content string, modelID string, sessionID string, sessionName string, usage map[string]interface{})
	OnChunk           func(text string)
	OnToolStart       func(name string, arguments map[string]interface{})
	OnToolEnd         func(name string, result map[string]interface{})
	OnToolOutput      func(name string, line string)
	OnRetry           func(attempt int, delay float64, message string)
	ConfirmPermission func(name string, desc string, args map[string]interface{}) bool
	OnError           func(message string)
}

type Client struct {
	cmd       *exec.Cmd
	conn      net.Conn
	callbacks *IPCCallbacks

	pending     map[int64]chan *JSONRPCMessage
	pendingLock sync.Mutex
	nextID      int64

	isClosed int32
}

func NewClient(callbacks *IPCCallbacks) *Client {
	return &Client{
		callbacks: callbacks,
		pending:   make(map[int64]chan *JSONRPCMessage),
		nextID:    1,
	}
}

func (c *Client) Start(projectRoot string, configPath string, opts map[string]interface{}) error {
	if c.cmd != nil {
		return errors.New("client sudah berjalan")
	}

	// 1. Buat TCP Listener pada localhost port random
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return fmt.Errorf("gagal membuat TCP listener: %v", err)
	}
	defer listener.Close()

	addr := listener.Addr().(*net.TCPAddr)
	port := addr.Port

	// Dapatkan path interpreter Python dari parent process
	pythonPath := os.Getenv("AUTOKEREN_PYTHON_PATH")
	if pythonPath == "" {
		// Cek apakah ada virtual environment lokal (.venv)
		localVenv := filepath.Join(projectRoot, ".venv", "bin", "python3")
		if _, err := os.Stat(localVenv); err == nil {
			pythonPath = localVenv
		} else {
			localVenvWin := filepath.Join(projectRoot, ".venv", "Scripts", "python.exe")
			if _, err := os.Stat(localVenvWin); err == nil {
				pythonPath = localVenvWin
			}
		}
	}

	if pythonPath == "" {
		// Fallback ke pencarian PATH biasa jika dijalankan terpisah
		var err error
		pythonPath, err = exec.LookPath("python3")
		if err != nil {
			pythonPath, err = exec.LookPath("python")
			if err != nil {
				return errors.New("interpreter python3 tidak ditemukan di PATH")
			}
		}
	}

	// 2. Jalankan subprocess Python daemon dengan melewatkan argumen port
	c.cmd = exec.Command(pythonPath, "-m", "autokeren.daemon", "--port", strconv.Itoa(port))
	c.cmd.Env = append(os.Environ(), "PYTHONPATH=.", "PYTHONUNBUFFERED=1")
	
	// Alihkan stdout & stderr daemon ke os.Stderr
	// Ini memisahkan stdout/print() Python biasa agar tidak mencemari JSON-RPC
	c.cmd.Stdout = os.Stderr
	c.cmd.Stderr = os.Stderr

	if err := c.cmd.Start(); err != nil {
		return fmt.Errorf("gagal menjalankan daemon: %v", err)
	}

	// 3. Terima koneksi incoming dari Python daemon
	// Set deadline agar tidak gantung selamanya jika daemon gagal meluncur
	if tcpListener, ok := listener.(*net.TCPListener); ok {
		tcpListener.SetDeadline(time.Now().Add(10 * time.Second))
	}
	conn, err := listener.Accept()
	if err != nil {
		c.cmd.Process.Kill()
		return fmt.Errorf("gagal menerima koneksi dari daemon: %v", err)
	}
	c.conn = conn

	// Mulai mendengarkan data di goroutine background
	go c.listen()

	// Kirim inisialisasi awal
	initParams := map[string]interface{}{
		"project_root": projectRoot,
	}
	if configPath != "" {
		initParams["config_path"] = configPath
	}
	for k, v := range opts {
		initParams[k] = v
	}

	var respStr string
	err = c.Call("agent.init", initParams, &respStr)
	if err != nil {
		c.Close()
		return fmt.Errorf("gagal inisialisasi agen: %v", err)
	}

	return nil
}

func (c *Client) Close() {
	if atomic.CompareAndSwapInt32(&c.isClosed, 0, 1) {
		if c.conn != nil {
			c.conn.Close()
		}
		if c.cmd != nil && c.cmd.Process != nil {
			c.cmd.Process.Kill()
		}
		GetBrowserManager().Close()
	}
}

func (c *Client) send(msg *JSONRPCMessage) error {
	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	data = append(data, '\n')

	c.pendingLock.Lock()
	defer c.pendingLock.Unlock()

	if atomic.LoadInt32(&c.isClosed) == 1 {
		return errors.New("ipc client closed")
	}

	_, err = c.conn.Write(data)
	return err
}

func (c *Client) Call(method string, params interface{}, reply interface{}) error {
	id := atomic.AddInt64(&c.nextID, 1)

	rawParams, err := json.Marshal(params)
	if err != nil {
		return err
	}

	ch := make(chan *JSONRPCMessage, 1)
	c.pendingLock.Lock()
	c.pending[id] = ch
	c.pendingLock.Unlock()

	defer func() {
		c.pendingLock.Lock()
		delete(c.pending, id)
		c.pendingLock.Unlock()
	}()

	msg := &JSONRPCMessage{
		JSONRPC: "2.0",
		Method:  method,
		Params:  rawParams,
		ID:      id,
	}

	if err := c.send(msg); err != nil {
		return err
	}

	// Tunggu response
	resp := <-ch
	if resp == nil {
		return errors.New("daemon process exited or disconnected")
	}

	if resp.Error != nil {
		return fmt.Errorf("daemon error (%d): %s", resp.Error.Code, resp.Error.Message)
	}

	if reply != nil && len(resp.Result) > 0 {
		return json.Unmarshal(resp.Result, reply)
	}

	return nil
}

func (c *Client) handleNotification(msg *JSONRPCMessage) {
	if c.callbacks == nil {
		return
	}

	switch msg.Method {
	case "ui.on_model_start":
		if c.callbacks.OnModelStart != nil {
			c.callbacks.OnModelStart()
		}
	case "ui.on_model_end":
		if c.callbacks.OnModelEnd != nil {
			var p struct {
				Content     string                 `json:"content"`
				ModelID     string                 `json:"model_id"`
				SessionID   string                 `json:"session_id"`
				SessionName string                 `json:"session_name"`
				Usage       map[string]interface{} `json:"usage"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnModelEnd(p.Content, p.ModelID, p.SessionID, p.SessionName, p.Usage)
			}
		}
	case "ui.on_chunk":
		if c.callbacks.OnChunk != nil {
			var p struct {
				Text string `json:"text"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnChunk(p.Text)
			}
		}
	case "ui.on_tool_start":
		if c.callbacks.OnToolStart != nil {
			var p struct {
				Name      string                 `json:"name"`
				Arguments map[string]interface{} `json:"arguments"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnToolStart(p.Name, p.Arguments)
			}
		}
	case "ui.on_tool_end":
		if c.callbacks.OnToolEnd != nil {
			var p struct {
				Name   string                 `json:"name"`
				Result map[string]interface{} `json:"result"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnToolEnd(p.Name, p.Result)
			}
		}
	case "ui.on_tool_output":
		if c.callbacks.OnToolOutput != nil {
			var p struct {
				Name string `json:"name"`
				Line string `json:"line"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnToolOutput(p.Name, p.Line)
			}
		}
	case "ui.on_retry":
		if c.callbacks.OnRetry != nil {
			var p struct {
				Attempt int     `json:"attempt"`
				Delay   float64 `json:"delay"`
				Message string  `json:"message"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnRetry(p.Attempt, p.Delay, p.Message)
			}
		}
	case "ui.error":
		if c.callbacks.OnError != nil {
			var p struct {
				Message string `json:"message"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnError(p.Message)
			}
		}
	}
}

func (c *Client) handleRequest(msg *JSONRPCMessage) {
	// Peta method request masuk dari Python (seperti ui.confirm_permission)
	if msg.Method == "ui.confirm_permission" {
		var p struct {
			ToolName    string                 `json:"tool_name"`
			Description string                 `json:"description"`
			Arguments   map[string]interface{} `json:"arguments"`
		}

		allowed := false
		if err := json.Unmarshal(msg.Params, &p); err == nil && c.callbacks != nil && c.callbacks.ConfirmPermission != nil {
			allowed = c.callbacks.ConfirmPermission(p.ToolName, p.Description, p.Arguments)
		}

		// Kirim balik hasil konfirmasi sebagai response
		resBytes, _ := json.Marshal(allowed)
		resp := &JSONRPCMessage{
			JSONRPC: "2.0",
			Result:  resBytes,
			ID:      msg.ID,
		}
		c.send(resp)
	} else if msg.Method == "ui.control_browser" {
		var p struct {
			Action string                 `json:"action"`
			Args   map[string]interface{} `json:"args"`
		}

		var result interface{}
		var err error
		if err = json.Unmarshal(msg.Params, &p); err == nil {
			bm := GetBrowserManager()
			result, err = bm.Execute(p.Action, p.Args)
		}

		respMap := map[string]interface{}{
			"ok":     err == nil,
			"output": result,
		}
		if err != nil {
			respMap["error"] = err.Error()
		}

		resBytes, _ := json.Marshal(respMap)
		resp := &JSONRPCMessage{
			JSONRPC: "2.0",
			Result:  resBytes,
			ID:      msg.ID,
		}
		c.send(resp)
	}
}

func (c *Client) listen() {
	scanner := bufio.NewScanner(c.conn)
	// Set buffer limit to 64MB to handle large payloads (like screenshots or file diffs)
	const maxCapacity = 64 * 1024 * 1024
	buf := make([]byte, 0, 64*1024)
	scanner.Buffer(buf, maxCapacity)

	for scanner.Scan() {
		data := scanner.Bytes()
		if len(data) == 0 {
			continue
		}

		var msg JSONRPCMessage
		if err := json.Unmarshal(data, &msg); err != nil {
			if c.callbacks != nil && c.callbacks.OnError != nil {
				c.callbacks.OnError(fmt.Sprintf("gagal parse pesan daemon: %v | raw: %s", err, string(data)))
			}
			continue
		}

		// Kasus 1: Notifikasi (method terisi, id kosong)
		if msg.Method != "" && msg.ID == nil {
			c.handleNotification(&msg)
			continue
		}

		// Kasus 2: Request masuk (method terisi, id terisi)
		if msg.Method != "" && msg.ID != nil {
			c.handleRequest(&msg)
			continue
		}

		// Kasus 3: Response atas request (id terisi, method kosong)
		if msg.ID != nil {
			var numericID int64
			// Nilai ID dari json unmarshal bisa bertipe float64
			if f, ok := msg.ID.(float64); ok {
				numericID = int64(f)
			} else if i, ok := msg.ID.(int64); ok {
				numericID = i
			}

			c.pendingLock.Lock()
			ch, ok := c.pending[numericID]
			c.pendingLock.Unlock()

			if ok {
				ch <- &msg
			}
		}
	}

	// Jika scanner selesai (daemon keluar)
	c.pendingLock.Lock()
	for _, ch := range c.pending {
		close(ch)
	}
	c.pending = make(map[int64]chan *JSONRPCMessage)
	c.pendingLock.Unlock()

	c.Close()
}

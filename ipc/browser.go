package ipc

import browser "github.com/autokeren/autokeren/internal/browser"

type BrowserManager = browser.BrowserManager

func GetBrowserManager() *BrowserManager { return browser.GetBrowserManager() }

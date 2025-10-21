import { useState, useEffect } from 'react'

function App() {
  const [activeTab, setActiveTab] = useState('servers')
  const [servers, setServers] = useState([])
  const [tools, setTools] = useState({})
  const [testOutput, setTestOutput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [anthropicKey, setAnthropicKey] = useState(localStorage.getItem('ANTHROPIC_API_KEY') || '')
  const [openaiKey, setOpenaiKey] = useState(localStorage.getItem('OPENAI_API_KEY') || '')

  useEffect(() => {
    fetchServers()
  }, [])

  const fetchServers = async () => {
    try {
      const res = await fetch('http://localhost:5000/api/servers')
      const data = await res.json()
      setServers(data.servers || [])
      setTools(data.tools || {})
    } catch (err) {
      console.error('Failed to fetch servers:', err)
    }
  }

  const runTest = async (testName) => {
    setLoading(true)
    setTestOutput('Running test...\n')
    try {
      const res = await fetch(`http://localhost:5000/api/run-test/${testName}`)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        setTestOutput(prev => prev + text)
      }
    } catch (err) {
      setTestOutput(prev => prev + `\nError: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const executeTool = async (serverName, toolName, args) => {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:5000/api/execute-tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ server: serverName, tool: toolName, args })
      })
      const data = await res.json()
      return data
    } catch (err) {
      console.error('Failed to execute tool:', err)
      return { error: err.message }
    } finally {
      setLoading(false)
    }
  }

  const saveApiKeys = () => {
    if (anthropicKey) localStorage.setItem('ANTHROPIC_API_KEY', anthropicKey)
    if (openaiKey) localStorage.setItem('OPENAI_API_KEY', openaiKey)
    
    // Send to backend to set in environment
    fetch('http://localhost:5000/api/set-env', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ANTHROPIC_API_KEY: anthropicKey,
        OPENAI_API_KEY: openaiKey
      })
    }).then(() => {
      setShowSettings(false)
      alert('API keys saved successfully!')
    }).catch(err => {
      console.error('Failed to save API keys:', err)
      alert('Failed to save API keys')
    })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-semibold text-slate-900">MCP Developer Portal</h1>
                <p className="text-sm text-slate-500">Magento Shopping Server Tools</p>
              </div>
            </div>
            <div className="relative">
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                title="API Settings"
              >
                <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
              
              {showSettings && (
                <div className="absolute right-0 mt-2 w-96 bg-white rounded-xl shadow-2xl border border-slate-200 p-6 z-50">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-900">API Keys</h3>
                    <button onClick={() => setShowSettings(false)} className="text-slate-400 hover:text-slate-600">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">
                        Anthropic API Key
                      </label>
                      <input
                        type="password"
                        value={anthropicKey}
                        onChange={(e) => setAnthropicKey(e.target.value)}
                        placeholder="sk-ant-..."
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">
                        OpenAI API Key
                      </label>
                      <input
                        type="password"
                        value={openaiKey}
                        onChange={(e) => setOpenaiKey(e.target.value)}
                        placeholder="sk-..."
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
                      />
                    </div>
                    
                    <button
                      onClick={saveApiKeys}
                      className="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                    >
                      Save Keys
                    </button>
                    
                    <p className="text-xs text-slate-500">
                      Keys are saved to a secure .env file on the backend and persist across server restarts.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1">
            {[
              { id: 'servers', label: 'Servers', icon: '🖥️' },
              { id: 'tools', label: 'Tools', icon: '🔧' },
              { id: 'tests', label: 'Tests', icon: '✓' },
              { id: 'executor', label: 'Executor', icon: '▶' },
              { id: 'taskrunner', label: 'Task Runner', icon: '🚀' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium transition-all duration-200 border-b-2 ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 bg-blue-50/50'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'servers' && <ServersTab servers={servers} />}
        {activeTab === 'tools' && <ToolsTab tools={tools} />}
        {activeTab === 'tests' && <TestsTab runTest={runTest} testOutput={testOutput} loading={loading} />}
        {activeTab === 'executor' && <ExecutorTab tools={tools} executeTool={executeTool} loading={loading} />}
        {activeTab === 'taskrunner' && <TaskRunnerTab />}
      </main>
    </div>
  )
}

function ServersTab({ servers }) {
  const [reconnecting, setReconnecting] = useState(null)

  const handleReconnect = async (serverName) => {
    setReconnecting(serverName)
    try {
      const res = await fetch(`http://localhost:5000/api/reconnect/${encodeURIComponent(serverName)}`, {
        method: 'POST'
      })
      const data = await res.json()
      if (data.status === 'connected') {
        window.location.reload()
      } else {
        alert(`Failed to reconnect: ${data.error || 'Unknown error'}`)
      }
    } catch (err) {
      alert(`Failed to reconnect: ${err.message}`)
    } finally {
      setReconnecting(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">MCP Servers</h2>
        <p className="text-slate-600">Persistent Model Context Protocol server connections</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {servers.map(server => (
          <div key={server.name} className="bg-white rounded-2xl border border-slate-200 p-6 hover:shadow-lg transition-all duration-200 hover:border-slate-300">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                  server.status === 'connected'
                    ? 'bg-gradient-to-br from-green-100 to-green-200'
                    : 'bg-gradient-to-br from-slate-100 to-slate-200'
                }`}>
                  <svg className={`w-6 h-6 ${server.status === 'connected' ? 'text-green-600' : 'text-slate-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{server.name}</h3>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 ${
                  server.status === 'connected' 
                    ? 'bg-green-100 text-green-700 border border-green-200' 
                    : 'bg-red-100 text-red-700 border border-red-200'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${server.status === 'connected' ? 'bg-green-500' : 'bg-red-500'}`}></span>
                  {server.status}
                </span>
              </div>
            </div>
            <p className="text-slate-600 text-sm mb-3">{server.description}</p>
            <div className="text-xs text-slate-500 font-mono bg-slate-50 px-3 py-2 rounded-lg border border-slate-200 mb-3">
              {server.path}
            </div>
            {server.status === 'disconnected' && (
              <button
                onClick={() => handleReconnect(server.name)}
                disabled={reconnecting === server.name}
                className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-slate-400 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {reconnecting === server.name ? (
                  <>
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Reconnecting...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Reconnect
                  </>
                )}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function ToolsTab({ tools }) {
  const [selectedTool, setSelectedTool] = useState(null)

  const allTools = Object.entries(tools).flatMap(([serverName, serverTools]) =>
    serverTools.map(tool => ({ ...tool, serverName }))
  )

  const currentTool = selectedTool || allTools[0]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">API Reference</h2>
        <p className="text-slate-600">Complete reference documentation for all available MCP tools</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left sidebar - Tool list */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden sticky top-24">
            <div className="p-4 border-b border-slate-200 bg-slate-50">
              <h3 className="font-semibold text-slate-900 text-sm">Available Tools</h3>
            </div>
            <div className="max-h-[calc(100vh-200px)] overflow-y-auto">
              {Object.entries(tools).map(([serverName, serverTools]) => (
                <div key={serverName}>
                  <div className="px-4 py-3 bg-slate-50 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-blue-100 rounded flex items-center justify-center">
                        <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                        </svg>
                      </div>
                      <span className="text-xs font-semibold text-slate-700">{serverName}</span>
                    </div>
                  </div>
                  {serverTools.map(tool => {
                    const isSelected = currentTool?.name === tool.name && currentTool?.serverName === serverName
                    return (
                      <button
                        key={tool.name}
                        onClick={() => setSelectedTool({ ...tool, serverName })}
                        className={`w-full text-left px-4 py-3 border-b border-slate-100 hover:bg-blue-50 transition-colors ${
                          isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : 'border-l-4 border-l-transparent'
                        }`}
                      >
                        <code className={`text-sm font-mono font-medium ${isSelected ? 'text-blue-700' : 'text-slate-700'}`}>
                          {tool.name}
                        </code>
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right content - Tool details */}
        <div className="lg:col-span-2">
          {currentTool && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6">
              {/* Header */}
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <code className="text-2xl font-semibold text-slate-900 font-mono">{currentTool.name}</code>
                  <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded border border-green-200">
                    MCP
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed">{currentTool.description}</p>
              </div>

              {/* Parameters */}
              {currentTool.inputSchema && currentTool.inputSchema.properties && (
                <div className="border-t border-slate-200 pt-6">
                  <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-4">Parameters</h4>
                  <div className="space-y-3">
                    {Object.entries(currentTool.inputSchema.properties).map(([param, schema]) => (
                      <div key={param} className="bg-slate-50 rounded-lg border border-slate-200 p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <code className="font-mono font-semibold text-slate-900">{param}</code>
                            <span className="text-sm text-slate-500">{schema.type}</span>
                          </div>
                          {currentTool.inputSchema.required?.includes(param) ? (
                            <span className="text-xs bg-rose-100 text-rose-700 px-2 py-1 rounded font-medium border border-rose-200">
                              required
                            </span>
                          ) : (
                            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded font-medium">
                              optional
                            </span>
                          )}
                        </div>
                        {schema.description && (
                          <p className="text-sm text-slate-600 leading-relaxed">{schema.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Example */}
              {currentTool.inputSchema && currentTool.inputSchema.properties && (
                <div className="border-t border-slate-200 pt-6">
                  <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-4">Example Request</h4>
                  <div className="bg-slate-900 rounded-lg p-4 overflow-x-auto">
                    <pre className="text-xs font-mono text-green-400">
{`{
  "method": "tools/call",
  "params": {
    "name": "${currentTool.name}",
    "arguments": {
${Object.entries(currentTool.inputSchema.properties)
  .filter(([param]) => currentTool.inputSchema.required?.includes(param))
  .map(([param, schema]) => {
    let exampleValue = schema.type === 'string' ? '"example"' : 
                       schema.type === 'number' ? '0' :
                       schema.type === 'boolean' ? 'false' : 'null'
    return `      "${param}": ${exampleValue}`
  })
  .join(',\n')}
    }
  }
}`}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TestsTab({ runTest, testOutput, loading }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Test Suite</h2>
        <p className="text-slate-600">Run integration tests to verify MCP server functionality</p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => runTest('quick')}
            disabled={loading}
            className="group relative bg-white border-2 border-blue-200 hover:border-blue-400 hover:bg-blue-50 disabled:border-slate-200 disabled:bg-slate-50 rounded-xl p-6 transition-all duration-200 text-left"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-100 group-hover:bg-blue-200 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900 mb-1">Quick Test</h3>
                <p className="text-sm text-slate-600">Smoke test - verifies basic connectivity and server availability</p>
              </div>
            </div>
          </button>
          
          <button
            onClick={() => runTest('full')}
            disabled={loading}
            className="group relative bg-white border-2 border-green-200 hover:border-green-400 hover:bg-green-50 disabled:border-slate-200 disabled:bg-slate-50 rounded-xl p-6 transition-all duration-200 text-left"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-green-100 group-hover:bg-green-200 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900 mb-1">Full Test</h3>
                <p className="text-sm text-slate-600">Integration test - validates all tools and database queries</p>
              </div>
            </div>
          </button>
        </div>
      </div>

      {testOutput && (
        <div className="bg-slate-900 rounded-2xl border border-slate-700 overflow-hidden shadow-2xl">
          <div className="bg-slate-800 px-6 py-4 border-b border-slate-700 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Test Output</h3>
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
            </div>
          </div>
          <pre className="p-6 font-mono text-sm text-green-400 whitespace-pre-wrap overflow-x-auto min-h-[300px]">
            {testOutput}
          </pre>
        </div>
      )}
    </div>
  )
}

function ExecutorTab({ tools, executeTool, loading }) {
  const [selectedServer, setSelectedServer] = useState('')
  const [selectedTool, setSelectedTool] = useState('')
  const [args, setArgs] = useState('{}')
  const [result, setResult] = useState(null)
  const [jsonError, setJsonError] = useState('')
  const [copied, setCopied] = useState(false)
  const [showArchitecture, setShowArchitecture] = useState(false)

  const serverNames = Object.keys(tools)
  const availableTools = selectedServer ? tools[selectedServer] || [] : []
  const selectedToolInfo = availableTools.find(t => t.name === selectedTool)

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const validateJson = (value) => {
    try {
      JSON.parse(value)
      setJsonError('')
      return true
    } catch (err) {
      setJsonError(err.message)
      return false
    }
  }

  const handleArgsChange = (value) => {
    setArgs(value)
    if (value.trim()) {
      validateJson(value)
    } else {
      setJsonError('')
    }
  }

  const handleExecute = async () => {
    if (!validateJson(args)) return
    
    try {
      const parsedArgs = JSON.parse(args)
      const res = await executeTool(selectedServer, selectedTool, parsedArgs)
      setResult(res)
    } catch (err) {
      setResult({ error: `Execution failed: ${err.message}` })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Tool Executor</h2>
          <p className="text-slate-600">Execute MCP tools with custom parameters</p>
        </div>
        <button
          onClick={() => setShowArchitecture(true)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white rounded-lg transition-all shadow-lg hover:shadow-xl text-sm font-medium"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          View Request Flow
        </button>
      </div>

      {showArchitecture && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-8 animate-fadeIn" style={{
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(12px)',
          margin: 0,
          padding: '2rem'
        }}>
          <div className="bg-gradient-to-br from-slate-900 via-blue-900 to-purple-900 rounded-3xl shadow-2xl w-full max-w-6xl h-[85vh] relative border border-blue-500/20 flex flex-col overflow-hidden">
            {/* Close button */}
            <button
              onClick={() => setShowArchitecture(false)}
              className="absolute top-6 right-6 w-10 h-10 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition-colors z-10"
            >
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Header */}
            <div className="px-10 py-6 border-b border-white/10">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-blue-400 to-purple-400 rounded-2xl flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-white">Request Flow Architecture</h3>
                  <p className="text-blue-200">Watch how your request travels through the system</p>
                </div>
              </div>
            </div>

            {/* Main content - horizontal flow */}
            <div className="flex-1 p-10 flex items-center justify-center">
              <div className="w-full max-w-5xl">
                {/* Top row: Browser -> Flask -> Docker boundary */}
                <div className="grid grid-cols-5 gap-6 mb-8">
                  {/* Browser */}
                  <div className="col-span-1 opacity-0 animate-slideIn" style={{ animationDelay: '0s', animationFillMode: 'forwards' }}>
                    <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/20 border-2 border-blue-400/40 rounded-2xl p-4 backdrop-blur-sm">
                      <div className="flex flex-col items-center gap-3">
                        <div className="w-16 h-16 bg-gradient-to-br from-blue-400 to-blue-500 rounded-xl flex items-center justify-center">
                          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                          </svg>
                        </div>
                        <div className="text-center">
                          <div className="text-white font-bold text-sm">Browser</div>
                          <div className="text-blue-200 text-xs">React UI</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Arrow */}
                  <div className="col-span-1 flex items-center justify-center opacity-0 animate-slideIn" style={{ animationDelay: '0.3s', animationFillMode: 'forwards' }}>
                    <div className="flex flex-col items-center">
                      <svg className="w-12 h-12 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                      <div className="text-blue-300 text-xs mt-1">HTTP POST</div>
                    </div>
                  </div>

                  {/* Flask Client */}
                  <div className="col-span-1 opacity-0 animate-slideIn" style={{ animationDelay: '0.6s', animationFillMode: 'forwards' }}>
                    <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/20 border-2 border-purple-400/40 rounded-2xl p-4 backdrop-blur-sm">
                      <div className="flex flex-col items-center gap-3">
                        <div className="w-16 h-16 bg-gradient-to-br from-purple-400 to-purple-500 rounded-xl flex items-center justify-center">
                          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <div className="text-center">
                          <div className="text-white font-bold text-sm">Flask</div>
                          <div className="text-purple-200 text-xs">MCPClient</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Arrow */}
                  <div className="col-span-1 flex items-center justify-center opacity-0 animate-slideIn" style={{ animationDelay: '0.9s', animationFillMode: 'forwards' }}>
                    <div className="flex flex-col items-center">
                      <svg className="w-12 h-12 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                      <div className="text-purple-300 text-xs mt-1">stdin/stdout</div>
                    </div>
                  </div>

                  {/* Docker Container */}
                  <div className="col-span-1 opacity-0 animate-slideIn" style={{ animationDelay: '1.2s', animationFillMode: 'forwards' }}>
                    <div className="bg-gradient-to-br from-cyan-500/20 to-cyan-600/20 border-2 border-cyan-400/40 rounded-2xl p-4 backdrop-blur-sm">
                      <div className="flex flex-col items-center gap-3">
                        <div className="w-16 h-16 bg-gradient-to-br from-cyan-400 to-cyan-500 rounded-xl flex items-center justify-center">
                          <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M13.983 11.078h2.119a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.119a.185.185 0 00-.185.185v1.888c0 .102.083.185.185.185m-2.954-5.43h2.118a.186.186 0 00.186-.186V3.574a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.185m0 2.716h2.118a.187.187 0 00.186-.186V6.29a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.887c0 .102.082.186.185.186m-2.93 0h2.12a.186.186 0 00.184-.186V6.29a.185.185 0 00-.185-.185H8.1a.185.185 0 00-.185.185v1.887c0 .102.083.186.185.186m-2.964 0h2.119a.186.186 0 00.185-.186V6.29a.185.185 0 00-.185-.185H5.136a.186.186 0 00-.186.185v1.887c0 .102.084.186.186.186m5.893 2.715h2.118a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.185m-2.93 0h2.12a.185.185 0 00.184-.185V9.006a.185.185 0 00-.184-.186h-2.12a.185.185 0 00-.184.185v1.888c0 .102.083.185.185.185m-2.964 0h2.119a.185.185 0 00.185-.185V9.006a.185.185 0 00-.184-.186h-2.12a.186.186 0 00-.186.186v1.887c0 .102.084.185.186.185m0-2.715h2.119a.186.186 0 00.185-.186V6.29a.185.185 0 00-.185-.185h-2.12a.186.186 0 00-.185.185v1.887c0 .102.084.186.186.186m-2.92 0h2.12a.185.185 0 00.184-.186V6.29a.185.185 0 00-.184-.185h-2.12a.185.185 0 00-.185.185v1.887c0 .102.084.186.185.186"/>
                          </svg>
                        </div>
                        <div className="text-center">
                          <div className="text-white font-bold text-sm">Docker</div>
                          <div className="text-cyan-200 text-xs">Container</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Docker container boundary */}
                <div className="relative opacity-0 animate-slideIn" style={{ animationDelay: '1.5s', animationFillMode: 'forwards' }}>
                  <div className="absolute inset-0 border-2 border-dashed border-cyan-400/50 rounded-3xl pointer-events-none"></div>
                  <div className="absolute -top-3 left-6 bg-gradient-to-br from-slate-900 to-blue-900 px-3 py-1 rounded-full border border-cyan-400/50">
                    <span className="text-cyan-300 text-xs font-bold">🐳 Inside Docker Container</span>
                  </div>
                  
                  {/* Bottom row: MCP Server -> MySQL (inside docker) */}
                  <div className="grid grid-cols-3 gap-6 p-8">
                    {/* MCP Server */}
                    <div className="col-span-1 opacity-0 animate-slideIn" style={{ animationDelay: '1.8s', animationFillMode: 'forwards' }}>
                      <div className="bg-gradient-to-br from-violet-500/20 to-violet-600/20 border-2 border-violet-400/40 rounded-2xl p-4 backdrop-blur-sm">
                        <div className="flex flex-col items-center gap-3">
                          <div className="w-16 h-16 bg-gradient-to-br from-violet-400 to-violet-500 rounded-xl flex items-center justify-center">
                            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                            </svg>
                          </div>
                          <div className="text-center">
                            <div className="text-white font-bold text-sm">MCP Server</div>
                            <div className="text-violet-200 text-xs">Python Process</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Arrow */}
                    <div className="col-span-1 flex items-center justify-center opacity-0 animate-slideIn" style={{ animationDelay: '2.1s', animationFillMode: 'forwards' }}>
                      <div className="flex flex-col items-center">
                        <svg className="w-12 h-12 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                        <div className="text-violet-300 text-xs mt-1">SQL Query</div>
                      </div>
                    </div>

                    {/* MySQL */}
                    <div className="col-span-1 opacity-0 animate-slideIn" style={{ animationDelay: '2.4s', animationFillMode: 'forwards' }}>
                      <div className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/20 border-2 border-emerald-400/40 rounded-2xl p-4 backdrop-blur-sm">
                        <div className="flex flex-col items-center gap-3">
                          <div className="w-16 h-16 bg-gradient-to-br from-emerald-400 to-emerald-500 rounded-xl flex items-center justify-center">
                            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                            </svg>
                          </div>
                          <div className="text-center">
                            <div className="text-white font-bold text-sm">MySQL</div>
                            <div className="text-emerald-200 text-xs">Database</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Performance banner */}
                <div className="mt-8 opacity-0 animate-slideIn" style={{ animationDelay: '2.7s', animationFillMode: 'forwards' }}>
                  <div className="bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border-2 border-yellow-400/40 rounded-2xl p-6 backdrop-blur-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-yellow-400 to-orange-400 rounded-xl flex items-center justify-center">
                          <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                          </svg>
                        </div>
                        <div>
                          <div className="text-yellow-200 font-bold text-lg">⚡ Persistent Connection = Lightning Speed</div>
                          <div className="text-yellow-100 text-sm">MCP server stays alive • No process spawning • Instant responses</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-4xl font-bold text-yellow-300">~0.6s</div>
                        <div className="text-yellow-200 text-xs">average response time</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <style>{`
            @keyframes fadeIn {
              from { opacity: 0; }
              to { opacity: 1; }
            }
            @keyframes slideIn {
              from {
                opacity: 0;
                transform: scale(0.9);
              }
              to {
                opacity: 1;
                transform: scale(1);
              }
            }
            .animate-fadeIn {
              animation: fadeIn 0.3s ease-out;
            }
            .animate-slideIn {
              animation: slideIn 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
            }
          `}</style>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">Select Server</label>
                <select
                  value={selectedServer}
                  onChange={(e) => {
                    setSelectedServer(e.target.value)
                    setSelectedTool('')
                    setResult(null)
                  }}
                  className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                >
                  <option value="">Choose a server...</option>
                  {serverNames.map(name => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">Select Tool</label>
                <select
                  value={selectedTool}
                  onChange={(e) => {
                    setSelectedTool(e.target.value)
                    setResult(null)
                  }}
                  disabled={!selectedServer}
                  className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all disabled:bg-slate-50 disabled:text-slate-400"
                >
                  <option value="">Choose a tool...</option>
                  {availableTools.map(tool => (
                    <option key={tool.name} value={tool.name}>{tool.name}</option>
                  ))}
                </select>
              </div>
            </div>

            {selectedToolInfo && (
              <details className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-2xl overflow-hidden">
                <summary className="cursor-pointer p-4 hover:bg-blue-100/50 transition-colors flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h4 className="font-semibold text-blue-900">Tool Information</h4>
                  </div>
                  <svg className="w-5 h-5 text-blue-600 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                
                <div className="px-5 pb-5 space-y-4">
                  <div>
                    <h5 className="text-xs font-semibold text-blue-900 uppercase tracking-wide mb-2">Description</h5>
                    <p className="text-sm text-blue-800 whitespace-pre-wrap">{selectedToolInfo.description}</p>
                  </div>
                  
                  {selectedToolInfo.inputSchema && selectedToolInfo.inputSchema.properties && (
                    <div className="pt-4 border-t border-blue-200">
                      <h5 className="text-xs font-semibold text-blue-900 uppercase tracking-wide mb-3">Parameters</h5>
                      <div className="space-y-2">
                        {Object.entries(selectedToolInfo.inputSchema.properties).map(([param, schema]) => (
                          <div key={param} className="bg-white/60 rounded-lg p-3 border border-blue-200">
                            <div className="flex items-center gap-2 mb-1">
                              <code className="font-mono font-semibold text-blue-700 text-sm">{param}</code>
                              {selectedToolInfo.inputSchema.required?.includes(param) ? (
                                <span className="text-xs bg-rose-100 text-rose-700 px-2 py-0.5 rounded-md font-medium border border-rose-200">
                                  required
                                </span>
                              ) : (
                                <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md font-medium border border-slate-200">
                                  optional
                                </span>
                              )}
                              <span className="text-xs text-slate-500">({schema.type})</span>
                            </div>
                            {schema.description && (
                              <p className="text-xs text-slate-600 mt-1">{schema.description}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </details>
            )}

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Arguments
                <span className="text-slate-500 font-normal ml-2">(JSON format)</span>
              </label>
              <textarea
                value={args}
                onChange={(e) => handleArgsChange(e.target.value)}
                className={`w-full bg-slate-50 border ${jsonError ? 'border-red-300 focus:ring-red-500' : 'border-slate-300 focus:ring-blue-500'} rounded-xl px-4 py-3 font-mono text-sm text-slate-900 focus:outline-none focus:ring-2 focus:border-transparent transition-all`}
                rows="8"
                placeholder='{\n  "product_id": "B006H52HBC"\n}'
              />
              {jsonError && (
                <div className="mt-2 flex items-start gap-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg border border-red-200">
                  <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span className="font-medium">Invalid JSON: {jsonError}</span>
                </div>
              )}
            </div>

            <button
              onClick={handleExecute}
              disabled={!selectedTool || loading || !!jsonError}
              className="w-full bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 disabled:from-slate-300 disabled:to-slate-400 text-white font-semibold py-4 px-6 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Executing...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Execute Tool</span>
                </>
              )}
            </button>
          </div>
        </div>

        <div className="lg:col-span-1">
          {result && (
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-lg sticky top-24">
              <div className="bg-gradient-to-r from-slate-800 to-slate-900 px-5 py-4 border-b border-slate-700 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Response
                </h3>
                <button
                  onClick={copyToClipboard}
                  className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-sm font-medium text-white"
                  title="Copy to clipboard"
                >
                  {copied ? (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
              <div className="p-5 max-h-[600px] overflow-y-auto">
                <pre className="text-xs font-mono text-slate-700 whitespace-pre-wrap break-words">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            </div>
          )}
          
          {!result && selectedTool && (
            <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl border-2 border-dashed border-slate-300 p-8 text-center">
              <div className="w-16 h-16 bg-slate-200 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
              </div>
              <p className="text-slate-500 text-sm font-medium">Execute a tool to see results here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TaskRunnerTab() {
  const [tasks, setTasks] = useState([])
  const [selectedTask, setSelectedTask] = useState('')
  const [website, setWebsite] = useState('shopping')
  const [headless, setHeadless] = useState(true)
  const [useMcp, setUseMcp] = useState(true)
  const [running, setRunning] = useState(false)
  const [output, setOutput] = useState('')
  const [taskResult, setTaskResult] = useState(null)
  const [detailedResults, setDetailedResults] = useState(null)
  const [copied, setCopied] = useState(false)
  const [selectedStep, setSelectedStep] = useState(0)
  const [showOutput, setShowOutput] = useState(true)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saveTags, setSaveTags] = useState('')
  const [saveNotes, setSaveNotes] = useState('')
  const [showSavedRuns, setShowSavedRuns] = useState(false)
  const [savedRuns, setSavedRuns] = useState([])
  const [loadingSavedRuns, setLoadingSavedRuns] = useState(false)
  
  // Batch mode state
  const [batchMode, setBatchMode] = useState(false)
  const [batchTaskIds, setBatchTaskIds] = useState('')
  const [batchResults, setBatchResults] = useState([])
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 })
  const [showBatchOutput, setShowBatchOutput] = useState(false)
  const [selectedBatchTask, setSelectedBatchTask] = useState(null)

  useEffect(() => {
    fetchTasks()
  }, [])

  const fetchTasks = async () => {
    try {
      const res = await fetch('http://localhost:5000/api/tasks')
      const data = await res.json()
      setTasks(data.tasks || [])
    } catch (err) {
      console.error('Failed to fetch tasks:', err)
    }
  }

  const runTask = async () => {
    if (!selectedTask) {
      alert('Please select a task')
      return
    }

    setRunning(true)
    setOutput('Starting task...\n')
    setTaskResult(null)

    try {
      const res = await fetch('http://localhost:5000/api/run-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_name: selectedTask,
          website: website,
          headless: headless,
          use_mcp: useMcp
        })
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let fullOutput = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        fullOutput += text
        setOutput(prev => prev + text)
      }

      // Check for success/failure
      const isSuccess = fullOutput.includes('[TASK COMPLETED SUCCESSFULLY]')
      const isFailed = fullOutput.includes('[TASK FAILED')
      
      // Extract result directory
      const resultDirMatch = fullOutput.match(/\[RESULT_DIR:([^\]]+)\]/)
      const resultDir = resultDirMatch ? resultDirMatch[1] : null
      
      if (isSuccess || isFailed) {
        setTaskResult({ 
          success: isSuccess, 
          message: isSuccess ? 'Task completed successfully!' : 'Task failed - check output for details',
          resultDir: resultDir
        })
        
        // Fetch detailed results if we have a result directory
        if (resultDir) {
          fetchDetailedResults(resultDir)
        }
      }
    } catch (err) {
      setOutput(prev => prev + `\nError: ${err.message}`)
      setTaskResult({ success: false, message: `Error: ${err.message}` })
    } finally {
      setRunning(false)
    }
  }

  const fetchDetailedResults = async (resultDir) => {
    try {
      console.log('Fetching results from:', resultDir)
      const res = await fetch(`http://localhost:5000/api/task-results/${resultDir}`)
      const data = await res.json()
      console.log('Received data:', data)
      
      if (data.error) {
        console.error('Error from backend:', data.error)
        return
      }
      
      setDetailedResults(data)
      setSelectedStep(0)
      setShowOutput(false)
      
      // Set raw output if available
      if (data.raw_output) {
        setOutput(data.raw_output)
      } else {
        setOutput('') // Clear previous output
      }
    } catch (err) {
      console.error('Failed to fetch detailed results:', err)
    }
  }

  const runBatchTasks = async () => {
    if (!batchTaskIds.trim()) {
      alert('Please enter task IDs')
      return
    }

    setRunning(true)
    setOutput('')
    setBatchResults([])
    setBatchProgress({ current: 0, total: 0 })
    setShowBatchOutput(true)

    try {
      const res = await fetch('http://localhost:5000/api/run-batch-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_ids: batchTaskIds,
          website: website,
          headless: headless,
          use_mcp: useMcp
        })
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const text = decoder.decode(value)
        const lines = text.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              switch (data.type) {
                case 'batch_start':
                  setBatchProgress({ current: 0, total: data.total_tasks })
                  setBatchResults(data.task_ids.map(id => ({ task_id: id, status: 'queued' })))
                  break
                
                case 'task_start':
                  setBatchProgress({ current: data.task_num, total: data.total })
                  setBatchResults(prev => prev.map(r => 
                    r.task_id === data.task_id ? { ...r, status: 'running' } : r
                  ))
                  break
                
                case 'task_output':
                  setOutput(prev => prev + data.line + '\n')
                  break
                
                case 'task_complete':
                  setBatchResults(prev => prev.map(r => 
                    r.task_id === data.task_id ? { ...r, ...data } : r
                  ))
                  break
                
                case 'task_error':
                  setBatchResults(prev => prev.map(r => 
                    r.task_id === data.task_id ? { ...r, status: 'error', error: data.error } : r
                  ))
                  break
                
                case 'batch_complete':
                  setBatchResults(data.results)
                  break
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }
    } catch (err) {
      setOutput(prev => prev + `\nError: ${err.message}`)
    } finally {
      setRunning(false)
    }
  }

  const selectedTaskInfo = tasks.find(t => t.name === selectedTask)

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(output)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const fetchSavedRuns = async () => {
    setLoadingSavedRuns(true)
    try {
      const res = await fetch('http://localhost:5000/api/saved-runs')
      const data = await res.json()
      setSavedRuns(data.runs || [])
    } catch (err) {
      console.error('Failed to fetch saved runs:', err)
    } finally {
      setLoadingSavedRuns(false)
    }
  }

  const saveCurrentRun = async () => {
    if (!detailedResults) return
    
    try {
      const tags = saveTags.split(',').map(t => t.trim()).filter(t => t)
      const res = await fetch('http://localhost:5000/api/saved-runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          result_dir: detailedResults.result_dir,
          name: saveName,
          tags: tags,
          notes: saveNotes,
          task_id: selectedTask
        })
      })
      
      const data = await res.json()
      if (data.success) {
        setShowSaveModal(false)
        setSaveName('')
        setSaveTags('')
        setSaveNotes('')
        fetchSavedRuns()
      }
    } catch (err) {
      console.error('Failed to save run:', err)
    }
  }

  const loadSavedRun = async (runId, runType) => {
    try {
      const res = await fetch(`http://localhost:5000/api/saved-runs/${runId}/results`)
      const data = await res.json()
      
      if (data.error) {
        console.error('Error loading saved run:', data.error)
        return
      }
      
      // Check if this is a batch run
      if (data.results && Array.isArray(data.results)) {
        // This is a batch run - load batch view
        console.log('Loading batch run:', data)
        setBatchMode(true)
        setBatchResults(data.results)
        setBatchTaskIds(data.task_ids.join(','))
        setShowSavedRuns(false)
        setShowOutput(false)
      } else {
        // Regular single run
        console.log('Loaded saved run data:', { hasRawOutput: !!data.raw_output, rawOutputLength: data.raw_output?.length })
        
        setDetailedResults(data)
        setSelectedStep(0)
        setShowOutput(false)
        setShowSavedRuns(false)
        setBatchMode(false)
        
        // Set raw output so "View Raw Output" button works
        if (data.raw_output) {
          console.log('Setting output from saved run')
          setOutput(data.raw_output)
        } else {
          console.warn('No raw_output in saved run data')
        }
      }
    } catch (err) {
      console.error('Failed to load saved run:', err)
    }
  }

  const deleteSavedRun = async (runId) => {
    if (!confirm('Are you sure you want to delete this saved run?')) return
    
    try {
      await fetch(`http://localhost:5000/api/saved-runs/${runId}`, {
        method: 'DELETE'
      })
      fetchSavedRuns()
    } catch (err) {
      console.error('Failed to delete saved run:', err)
    }
  }

  useEffect(() => {
    if (showSavedRuns) {
      fetchSavedRuns()
    }
  }, [showSavedRuns])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">WebArena Task Runner</h2>
          <p className="text-slate-600">Execute MCP-enabled WebArena tasks and monitor results</p>
        </div>
        <button
          onClick={() => setShowSavedRuns(true)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white font-medium rounded-lg shadow-lg transition-all"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
          Saved Runs ({savedRuns.length})
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Task Configuration
              </h3>
              
              {/* Batch Mode Toggle */}
              <div className="flex items-center gap-2 bg-slate-100 rounded-lg p-1">
                <button
                  onClick={() => setBatchMode(false)}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${!batchMode ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
                  disabled={running}
                >
                  Single
                </button>
                <button
                  onClick={() => setBatchMode(true)}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${batchMode ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
                  disabled={running}
                >
                  Batch
                </button>
              </div>
            </div>

            <div className="space-y-4">
              {!batchMode ? (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Select Task
                  </label>
                <select
                  value={selectedTask}
                  onChange={(e) => setSelectedTask(e.target.value)}
                  className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-900"
                  disabled={running}
                >
                  <option value="">Choose a task...</option>
                  {tasks.map(task => (
                    <option key={task.name} value={task.name}>
                      {task.name} - {task.intent.substring(0, 60)}...
                    </option>
                  ))}
                </select>
                
                {selectedTaskInfo && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                    <p className="text-sm font-medium text-blue-900 mb-1">Task Intent:</p>
                    <p className="text-sm text-blue-700">{selectedTaskInfo.intent}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded">
                        {selectedTaskInfo.sites.join(', ')}
                      </span>
                    </div>
                  </div>
                )}
              </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Task IDs
                    <span className="text-slate-500 text-xs ml-2">(e.g., "21,22,24-26")</span>
                  </label>
                  <input
                    type="text"
                    value={batchTaskIds}
                    onChange={(e) => setBatchTaskIds(e.target.value)}
                    placeholder="21,22,24-26"
                    className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-900"
                    disabled={running}
                  />
                  <p className="mt-2 text-xs text-slate-500">
                    Enter task IDs separated by commas. Use ranges like "24-26" for consecutive tasks.
                  </p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Website
                </label>
                <div className="w-full px-4 py-2.5 bg-slate-100 border border-slate-300 rounded-lg text-slate-700">
                  Shopping
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="use-mcp"
                    checked={useMcp}
                    onChange={(e) => setUseMcp(e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
                    disabled={running}
                  />
                  <label htmlFor="use-mcp" className="text-sm font-medium text-slate-700">
                    Enable MCP
                  </label>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="headless"
                    checked={headless}
                    onChange={(e) => setHeadless(e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
                    disabled={running}
                  />
                  <label htmlFor="headless" className="text-sm font-medium text-slate-700">
                    Run in headless mode
                  </label>
                </div>
              </div>

              <button
                onClick={batchMode ? runBatchTasks : runTask}
                disabled={running || (!batchMode && !selectedTask) || (batchMode && !batchTaskIds.trim())}
                className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:from-slate-400 disabled:to-slate-500 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
              >
                {running ? (
                  <>
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {batchMode ? `Running (${batchProgress.current}/${batchProgress.total})...` : 'Running Task...'}
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {batchMode ? 'Run Batch' : 'Execute Task'}
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Batch Results Table */}
          {batchMode && batchResults.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-lg">
              <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Batch Progress
                {!running && (
                  <span className="ml-auto text-sm font-normal text-slate-600">
                    {batchResults.filter(r => r.status === 'success').length}/{batchResults.length} passed
                  </span>
                )}
              </h3>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Task ID</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Status</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Steps</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Time</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batchResults.map((result) => (
                      <tr key={result.task_id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="py-3 px-4">
                          <span className="font-mono text-sm font-medium text-slate-900">
                            {result.task_id}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {result.status === 'success' && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded">
                              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                              </svg>
                              Pass
                            </span>
                          )}
                          {result.status === 'failed' && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded">
                              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                              </svg>
                              Fail
                            </span>
                          )}
                          {result.status === 'running' && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                              <div className="w-3 h-3 border-2 border-blue-700 border-t-transparent rounded-full animate-spin"></div>
                              Running
                            </span>
                          )}
                          {result.status === 'queued' && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded">
                              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                              </svg>
                              Queued
                            </span>
                          )}
                          {result.status === 'error' && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded">
                              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                              </svg>
                              Error
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-sm text-slate-600">
                          {result.n_steps !== undefined ? result.n_steps : '-'}
                        </td>
                        <td className="py-3 px-4 text-sm text-slate-600">
                          {result.elapsed_time ? `${result.elapsed_time}s` : '-'}
                        </td>
                        <td className="py-3 px-4">
                          {result.result_dir && (
                            <button
                              onClick={() => {
                                fetchDetailedResults(result.result_dir)
                                setBatchMode(false)
                                setShowOutput(false)
                              }}
                              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                            >
                              View
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {detailedResults && !showOutput ? (
            <div className="space-y-6">
              {/* Trajectory Timeline */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  Agent Trajectory ({detailedResults.screenshots ? detailedResults.screenshots.length : 0} states)
                </h3>
                
                <div className="flex gap-2 overflow-x-auto pb-2">
                  {(detailedResults.screenshots || []).map((screenshot, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedStep(idx)}
                      className={`flex-shrink-0 px-4 py-2 rounded-lg border-2 transition-all ${
                        selectedStep === idx
                          ? 'border-blue-500 bg-blue-50 text-blue-900'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <div className="text-xs font-medium">
                        {idx === 0 ? 'Initial' : `After Action ${idx}`}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Step Details */}
              {selectedStep === 0 ? (
                <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-lg">
                  <h3 className="text-lg font-semibold text-slate-900 mb-4">Initial State</h3>
                  <p className="text-slate-600">This is the browser state before the agent takes any actions.</p>
                </div>
              ) : detailedResults.actions && detailedResults.actions[selectedStep - 1] && (
                <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-lg">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-900">Action {selectedStep} - Agent Reasoning</h3>
                    <button
                      onClick={() => {
                        console.log('View Raw Output clicked - output exists:', !!output, 'showOutput will be:', true)
                        setShowOutput(true)
                      }}
                      className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      View Raw Output
                    </button>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                    <pre className="text-sm text-slate-700 whitespace-pre-wrap font-mono">
                      {detailedResults.actions[selectedStep - 1].action}
                    </pre>
                  </div>
                  
                  {/* OpenAI Evaluation Info */}
                  {detailedResults.openai_evals && detailedResults.openai_evals.filter(e => e.step === selectedStep - 1).length > 0 && (
                    <div className="mt-4 bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-8 h-8 bg-amber-500 rounded-full flex items-center justify-center">
                          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <div className="flex-grow">
                          <h4 className="text-sm font-semibold text-amber-900 mb-1">OpenAI Action Evaluation</h4>
                          <p className="text-xs text-amber-700 mb-2">
                            An OpenAI GPT model was used to evaluate this action after it was generated by Claude.
                          </p>
                          {detailedResults.openai_evals.filter(e => e.step === selectedStep - 1).map((evaluation, idx) => (
                            <div key={idx} className="bg-white bg-opacity-60 rounded p-2 mt-2">
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div>
                                  <span className="font-medium text-amber-900">Purpose:</span>
                                  <span className="text-amber-700 ml-1">{evaluation.purpose}</span>
                                </div>
                                <div>
                                  <span className="font-medium text-amber-900">Status:</span>
                                  <span className="text-amber-700 ml-1">{evaluation.status}</span>
                                </div>
                              </div>
                            </div>
                          ))}
                          <p className="text-xs text-amber-600 mt-2 italic">
                            Note: The specific evaluation response is not captured in logs. This evaluation happens during task execution to provide feedback on action quality.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Screenshot */}
              {detailedResults.screenshots && detailedResults.screenshots[selectedStep] && (
                <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-lg">
                  <div className="bg-gradient-to-r from-slate-800 to-slate-900 px-5 py-4">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      Browser State - Step {selectedStep}
                    </h3>
                  </div>
                  <div className="p-4 bg-slate-50">
                    <img 
                      src={detailedResults.is_saved_run 
                        ? `http://localhost:5000/api/saved-runs/${detailedResults.result_dir}/screenshot/${detailedResults.screenshots[selectedStep].filename}`
                        : `http://localhost:5000/api/task-results/${detailedResults.result_dir}/screenshot/${detailedResults.screenshots[selectedStep].filename}`}
                      alt={`Step ${selectedStep}`}
                      className="w-full rounded-lg border border-slate-300"
                    />
                  </div>
                </div>
              )}
            </div>
          ) : output && showOutput ? (
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-lg">
              <div className="bg-gradient-to-r from-slate-800 to-slate-900 px-5 py-4 border-b border-slate-700 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  Task Output
                </h3>
                <div className="flex items-center gap-2">
                  {detailedResults && (
                    <button
                      onClick={() => setShowOutput(false)}
                      className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-sm font-medium text-white"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                      <span>View Trajectory</span>
                    </button>
                  )}
                  <button
                    onClick={copyToClipboard}
                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-sm font-medium text-white"
                    title="Copy to clipboard"
                  >
                    {copied ? (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
              <div className="p-5 bg-slate-900 max-h-[600px] overflow-y-auto">
                <pre className="text-xs font-mono text-green-400 whitespace-pre-wrap break-words">
                  {output}
                </pre>
              </div>
            </div>
          ) : null}
        </div>

        <div className="lg:col-span-1 space-y-6">
          {taskResult && detailedResults && (
            <>
              {/* Status Card */}
              <div className={`rounded-2xl border-2 p-6 shadow-lg ${
                taskResult.success
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}>
                <div className="flex items-center gap-3 mb-4">
                  {taskResult.success ? (
                    <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                      <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  ) : (
                    <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                      <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  )}
                  <div>
                    <h3 className={`text-lg font-semibold ${taskResult.success ? 'text-green-900' : 'text-red-900'}`}>
                      {taskResult.success ? 'Success' : 'Failed'}
                    </h3>
                    <p className={`text-sm ${taskResult.success ? 'text-green-700' : 'text-red-700'}`}>
                      Reward: {detailedResults.reward.toFixed(2)}
                    </p>
                  </div>
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className={taskResult.success ? 'text-green-700' : 'text-red-700'}>Steps Taken:</span>
                    <span className={`font-semibold ${taskResult.success ? 'text-green-900' : 'text-red-900'}`}>{detailedResults.n_steps}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className={taskResult.success ? 'text-green-700' : 'text-red-700'}>Status:</span>
                    <span className={`font-semibold ${taskResult.success ? 'text-green-900' : 'text-red-900'}`}>
                      {detailedResults.terminated ? 'Terminated' : detailedResults.truncated ? 'Truncated' : 'Unknown'}
                    </span>
                  </div>
                </div>
                
                {/* Save Run Button */}
                {!detailedResults.is_saved_run && (
                  <button
                    onClick={() => {
                      setSaveName(`Task ${selectedTask} - ${new Date().toLocaleString()}`)
                      setShowSaveModal(true)
                    }}
                    className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-medium rounded-lg shadow-lg transition-all"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                    </svg>
                    Save This Run
                  </button>
                )}
              </div>

              {/* Performance Metrics */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Performance
                </h3>
                <div className="space-y-3">
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-xs text-slate-600 mb-1">Total Time</div>
                    <div className="text-xl font-bold text-slate-900">{detailedResults.stats.total_time.toFixed(2)}s</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-xs text-slate-600 mb-1">Agent Time</div>
                    <div className="text-xl font-bold text-slate-900">{detailedResults.stats.agent_time.toFixed(2)}s</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-xs text-slate-600 mb-1">Tokens Used</div>
                    <div className="text-xl font-bold text-slate-900">{detailedResults.stats.tokens_used.toLocaleString()}</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-xs text-slate-600 mb-1">Est. Cost (Haiku 4.5)</div>
                    <div className="text-xl font-bold text-slate-900">
                      ${(
                        (detailedResults.stats.input_tokens / 1000000) * 1.00 + 
                        (detailedResults.stats.output_tokens / 1000000) * 5.00
                      ).toFixed(4)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Why Failed */}
              {!taskResult.success && (
                <div className="bg-amber-50 border-2 border-amber-200 rounded-2xl p-6 shadow-lg">
                  <h3 className="text-lg font-semibold text-amber-900 mb-2 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    Why it failed
                  </h3>
                  <div className="text-sm text-amber-800 space-y-2">
                    {detailedResults.reward === 0 && (
                      <p>• Task goal not achieved (reward = 0)</p>
                    )}
                    {detailedResults.truncated && (
                      <p>• Reached maximum step limit ({detailedResults.n_steps} steps)</p>
                    )}
                    {detailedResults.error && (
                      <p>• Error: {detailedResults.error}</p>
                    )}
                    {!detailedResults.error && !detailedResults.truncated && (
                      <p>• Agent terminated without achieving goal</p>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          {taskResult && !detailedResults && (
            <div className={`rounded-2xl border-2 p-6 shadow-lg ${
              taskResult.success
                ? 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center gap-3 mb-4">
                {taskResult.success ? (
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                ) : (
                  <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                )}
                <div>
                  <h3 className={`text-lg font-semibold ${taskResult.success ? 'text-green-900' : 'text-red-900'}`}>
                    {taskResult.success ? 'Success' : 'Failed'}
                  </h3>
                  <p className={`text-sm ${taskResult.success ? 'text-green-700' : 'text-red-700'}`}>
                    {taskResult.message}
                  </p>
                </div>
              </div>
            </div>
          )}

          {!taskResult && !running && (
            <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl border-2 border-dashed border-slate-300 p-8 text-center">
              <div className="w-16 h-16 bg-slate-200 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <p className="text-slate-500 text-sm font-medium">Select and execute a task to see results</p>
            </div>
          )}

          {running && (
            <div className="bg-blue-50 border-2 border-blue-200 rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-3">
                <svg className="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <div>
                  <h3 className="text-lg font-semibold text-blue-900">Task Running</h3>
                  <p className="text-sm text-blue-700">Processing your request...</p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="h-2 bg-blue-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-600 rounded-full animate-pulse" style={{width: '100%'}}></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Save Run Modal */}
      {showSaveModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowSaveModal(false)}>
          <div className="bg-white rounded-2xl p-6 max-w-md w-full m-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-xl font-bold text-slate-900 mb-4">Save Task Run</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Run Name</label>
                <input
                  type="text"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g., Task 21 - Baseline"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Tags</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {['success', 'failure', 'mcp-enabled'].map(tag => {
                    const isActive = saveTags.split(',').map(t => t.trim()).includes(tag)
                    return (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => {
                          const currentTags = saveTags.split(',').map(t => t.trim()).filter(t => t)
                          if (isActive) {
                            // Remove tag
                            const newTags = currentTags.filter(t => t !== tag)
                            setSaveTags(newTags.join(', '))
                          } else {
                            // Add tag
                            setSaveTags([...currentTags, tag].join(', '))
                          }
                        }}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                          isActive
                            ? 'bg-blue-600 text-white'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        {tag}
                      </button>
                    )
                  })}
                </div>
                <input
                  type="text"
                  value={saveTags}
                  onChange={(e) => setSaveTags(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  placeholder="Add custom tags (comma-separated)"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Notes (optional)</label>
                <textarea
                  value={saveNotes}
                  onChange={(e) => setSaveNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  rows={3}
                  placeholder="Add notes about this run..."
                />
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowSaveModal(false)}
                className="flex-1 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveCurrentRun}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Saved Runs Panel */}
      {showSavedRuns && (
        <div className="fixed inset-0 z-50 flex justify-end" style={{ margin: 0, padding: 0, background: 'rgba(0, 0, 0, 0.5)' }} onClick={() => setShowSavedRuns(false)}>
          <div className="bg-white w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col h-full" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 to-purple-700 p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold text-white">Saved Runs</h3>
                <button
                  onClick={() => setShowSavedRuns(false)}
                  className="text-white hover:bg-white hover:bg-opacity-20 rounded-lg p-2 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <p className="text-purple-100 mt-2">{savedRuns.length} saved task runs</p>
            </div>

            {/* Saved Runs List */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {loadingSavedRuns ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
                </div>
              ) : savedRuns.length === 0 ? (
                <div className="text-center py-12">
                  <svg className="w-16 h-16 text-slate-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                  </svg>
                  <p className="text-slate-500 text-lg">No saved runs yet</p>
                  <p className="text-slate-400 text-sm mt-2">Run a task and save it for later analysis</p>
                </div>
              ) : (
                savedRuns.map(run => (
                  <div key={run.id} className="bg-white border-2 border-slate-200 rounded-xl p-4 hover:border-purple-300 transition-all">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          {run.type === 'batch' ? (
                            <>
                              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-semibold rounded">
                                Batch ({run.task_ids?.length || 0} tasks)
                              </span>
                              <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-semibold rounded">
                                {run.success_count}/{run.total} passed
                              </span>
                            </>
                          ) : (
                            <>
                              <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-semibold rounded">
                                Task {run.task_id}
                              </span>
                              {run.success ? (
                                <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-semibold rounded">Success</span>
                              ) : (
                                <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-semibold rounded">Failed</span>
                              )}
                            </>
                          )}
                        </div>
                        <h4 className="font-semibold text-slate-900 mb-1">{run.name}</h4>
                        <p className="text-xs text-slate-500">
                          {new Date(run.timestamp).toLocaleString()}
                          {run.type !== 'batch' && ` • ${run.n_steps} steps • Reward: ${run.reward}`}
                        </p>
                      </div>
                    </div>

                    {run.tags && run.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-3">
                        {run.tags.map((tag, idx) => (
                          <span key={idx} className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}

                    {run.notes && (
                      <p className="text-sm text-slate-600 mb-3 italic">{run.notes}</p>
                    )}

                    <div className="flex gap-2">
                      <button
                        onClick={() => loadSavedRun(run.id)}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors text-sm font-medium"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        Load
                      </button>
                      <button
                        onClick={() => deleteSavedRun(run.id)}
                        className="px-3 py-2 border border-red-300 text-red-600 hover:bg-red-50 rounded-lg transition-colors text-sm font-medium"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App

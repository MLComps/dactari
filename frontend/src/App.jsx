import { useState, useRef, useEffect, useCallback } from 'react'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [liveTranscript, setLiveTranscript] = useState('')
  const [streamingResponse, setStreamingResponse] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [playingId, setPlayingId] = useState(null)
  const [handoffData, setHandoffData] = useState(null)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const mediaRecorder = useRef(null)
  const audioChunks = useRef([])
  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const audioPlayerRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingResponse])

  // Initialize WebSocket connection
  const initWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws/voice`

    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'transcription':
          setLiveTranscript(data.text)
          if (!data.interim) {
            // Final transcription - add as user message
            if (data.text.trim()) {
              setMessages(prev => [...prev, {
                id: Date.now(),
                role: 'user',
                content: data.text
              }])
            }
            setLiveTranscript('')
          }
          break

        case 'response':
          setIsStreaming(true)
          setStreamingResponse(prev => prev + data.text)
          break

        case 'response_complete':
          setIsStreaming(false)
          setMessages(prev => [...prev, {
            id: Date.now(),
            role: 'assistant',
            content: data.full_text
          }])
          setStreamingResponse('')
          setIsLoading(false)
          break

        case 'audio':
          // Play the audio response
          playAudioFromBase64(data.data)
          break

        case 'error':
          console.error('WebSocket error:', data.message)
          setIsLoading(false)
          setIsStreaming(false)
          break
      }
    }

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    wsRef.current.onclose = () => {
      // Reconnect after a delay
      setTimeout(initWebSocket, 2000)
    }
  }, [])

  useEffect(() => {
    initWebSocket()
    return () => {
      wsRef.current?.close()
    }
  }, [initWebSocket])

  // Play audio from base64
  const playAudioFromBase64 = (base64Data) => {
    const audioData = atob(base64Data)
    const arrayBuffer = new ArrayBuffer(audioData.length)
    const view = new Uint8Array(arrayBuffer)
    for (let i = 0; i < audioData.length; i++) {
      view[i] = audioData.charCodeAt(i)
    }

    const blob = new Blob([arrayBuffer], { type: 'audio/mpeg' })
    const url = URL.createObjectURL(blob)

    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause()
    }

    audioPlayerRef.current = new Audio(url)
    audioPlayerRef.current.play()
  }

  // Send text message (non-voice)
  const sendMessage = async (text) => {
    if (!text.trim() || isLoading) return

    const userMsg = { id: Date.now(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)
    setStreamingResponse('')
    setIsStreaming(true)

    try {
      const allMessages = [...messages, userMsg].map(m => ({ role: m.role, content: m.content }))

      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: allMessages, voice_response: false })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullResponse = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'text') {
                fullResponse += data.content
                setStreamingResponse(fullResponse)
              } else if (data.type === 'done') {
                setMessages(prev => [...prev, {
                  id: Date.now(),
                  role: 'assistant',
                  content: data.full_response
                }])
              }
            } catch (e) {}
          }
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        error: true
      }])
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
      setStreamingResponse('')
    }
  }

  // Start voice recording with real-time transcription
  const startRecording = async () => {
    try {
      // Ensure WebSocket is connected
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        initWebSocket()
        await new Promise(resolve => setTimeout(resolve, 500))
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // Create MediaRecorder
      mediaRecorder.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })

      audioChunks.current = []

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunks.current.push(e.data)
          // Send audio chunk to WebSocket for real-time transcription
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            e.data.arrayBuffer().then(buffer => {
              wsRef.current.send(buffer)
            })
          }
        }
      }

      mediaRecorder.current.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
      }

      // Record in small chunks for real-time transcription
      mediaRecorder.current.start(500) // 500ms chunks
      setIsRecording(true)
      setLiveTranscript('')

    } catch (err) {
      console.error('Mic error:', err)
    }
  }

  // Stop recording and get final transcription + AI response
  const stopRecording = () => {
    if (mediaRecorder.current && isRecording) {
      mediaRecorder.current.stop()
      setIsRecording(false)
      setIsLoading(true)

      // Tell WebSocket we're done recording
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'stop',
          voice_response: true // Request voice response
        }))
      }
    }
  }

  // Play TTS for a specific message
  const playTTS = async (id, text) => {
    if (playingId === id) {
      audioPlayerRef.current?.pause()
      setPlayingId(null)
      return
    }

    setPlayingId(id)
    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      })
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)

      audioPlayerRef.current = new Audio(url)
      audioPlayerRef.current.onended = () => setPlayingId(null)
      audioPlayerRef.current.play()
    } catch {
      setPlayingId(null)
    }
  }

  // Download handoff PDF
  const downloadHandoff = async () => {
    const res = await fetch('/api/handoff', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(handoffData)
    })
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'clinical-handoff.pdf'
    a.click()
  }

  return (
    <div className="h-screen flex flex-col bg-[--bg-base]">
      {/* Header */}
      <header className="flex-shrink-0 h-16 border-b border-[--border] bg-[--bg-surface]">
        <div className="h-full max-w-3xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
              </svg>
            </div>
            <div>
              <h1 className="text-[15px] font-semibold text-[--text-primary]">Daktari</h1>
              <p className="text-xs text-[--text-muted]">Medical Assistant</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {handoffData && (
              <button onClick={downloadHandoff} className="h-9 px-4 flex items-center gap-2 text-sm font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-lg transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                </svg>
                Handoff PDF
              </button>
            )}
            <button onClick={() => { setMessages([]); setHandoffData(null) }} className="h-9 px-4 text-sm font-medium text-[--text-secondary] hover:text-[--text-primary] hover:bg-[--bg-elevated] rounded-lg transition-colors">
              New Chat
            </button>
          </div>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-6">
          {messages.length === 0 && !streamingResponse && !liveTranscript ? (
            <div className="h-full min-h-[70vh] flex flex-col items-center justify-center text-center py-20">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center mb-8 shadow-lg shadow-emerald-500/25">
                <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
                </svg>
              </div>

              <h1 className="text-3xl font-semibold text-[--text-primary] mb-3">
                How can I help you today?
              </h1>
              <p className="text-lg text-[--text-secondary] max-w-md mb-8">
                Describe your symptoms. I'll help prepare a clinical handoff note.
              </p>

              <div className="flex items-center gap-4 mb-8">
                <button
                  onClick={startRecording}
                  className="flex items-center gap-2 px-6 py-3 bg-emerald-500 hover:bg-emerald-400 text-white font-medium rounded-xl transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                  </svg>
                  Start Speaking
                </button>
                <span className="text-[--text-muted]">or type below</span>
              </div>

              <div className="grid grid-cols-2 gap-3 w-full max-w-lg">
                {[
                  { text: "I have a headache and fever", icon: "🤒" },
                  { text: "I've been coughing for 3 days", icon: "🫁" },
                  { text: "I have chest pain", icon: "💔" },
                  { text: "My child has a rash", icon: "👶" }
                ].map((item, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(item.text)}
                    className="flex items-center gap-3 p-4 text-left text-sm text-[--text-secondary] bg-[--bg-surface] hover:bg-[--bg-elevated] border border-[--border] hover:border-[--border-strong] rounded-xl transition-all"
                  >
                    <span className="text-xl">{item.icon}</span>
                    <span>{item.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="py-8 space-y-6">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in`}>
                  <div className={`flex gap-3 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center ${
                      msg.role === 'user'
                        ? 'bg-blue-500'
                        : 'bg-gradient-to-br from-emerald-400 to-emerald-600'
                    }`}>
                      {msg.role === 'user' ? (
                        <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
                        </svg>
                      )}
                    </div>

                    <div className="space-y-2">
                      <div className={`px-4 py-3 rounded-2xl ${
                        msg.role === 'user'
                          ? 'bg-blue-500 text-white rounded-tr-md'
                          : msg.error
                          ? 'bg-red-500/10 text-red-400 border border-red-500/20 rounded-tl-md'
                          : 'bg-[--bg-surface] text-[--text-primary] border border-[--border] rounded-tl-md'
                      }`}>
                        <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                      </div>

                      {msg.role === 'assistant' && !msg.error && (
                        <button
                          onClick={() => playTTS(msg.id, msg.content)}
                          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                            playingId === msg.id
                              ? 'text-emerald-400 bg-emerald-500/10'
                              : 'text-[--text-muted] hover:text-[--text-secondary] hover:bg-[--bg-surface]'
                          }`}
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
                          </svg>
                          {playingId === msg.id ? 'Playing...' : 'Listen'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Live transcription while recording */}
              {isRecording && liveTranscript && (
                <div className="flex justify-end animate-in">
                  <div className="flex gap-3 max-w-[80%] flex-row-reverse">
                    <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                      </svg>
                    </div>
                    <div className="px-4 py-3 bg-blue-500/20 border border-blue-500/30 text-blue-300 rounded-2xl rounded-tr-md">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                        <p className="text-[15px] italic">{liveTranscript}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Streaming response */}
              {isStreaming && streamingResponse && (
                <div className="flex justify-start animate-in">
                  <div className="flex gap-3 max-w-[80%]">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
                      </svg>
                    </div>
                    <div className="px-4 py-3 bg-[--bg-surface] text-[--text-primary] border border-[--border] rounded-2xl rounded-tl-md">
                      <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{streamingResponse}<span className="animate-pulse">▌</span></p>
                    </div>
                  </div>
                </div>
              )}

              {/* Loading without streaming */}
              {isLoading && !isStreaming && !streamingResponse && (
                <div className="flex justify-start animate-in">
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
                      </svg>
                    </div>
                    <div className="px-4 py-3 bg-[--bg-surface] border border-[--border] rounded-2xl rounded-tl-md">
                      <div className="flex gap-1.5">
                        <span className="typing-dot w-2 h-2 bg-emerald-400 rounded-full" />
                        <span className="typing-dot w-2 h-2 bg-emerald-400 rounded-full" />
                        <span className="typing-dot w-2 h-2 bg-emerald-400 rounded-full" />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input */}
      <div className="flex-shrink-0 border-t border-[--border] bg-[--bg-surface]">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            {/* Mic button */}
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isLoading && !isRecording}
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                isRecording
                  ? 'bg-red-500 text-white recording-pulse'
                  : 'bg-[--bg-elevated] text-[--text-secondary] hover:text-[--text-primary] hover:bg-[--bg-hover] border border-[--border]'
              } disabled:opacity-50`}
            >
              {isRecording ? (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                </svg>
              )}
            </button>

            {/* Input field */}
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage(input))}
                placeholder={isRecording ? "Listening..." : "Describe your symptoms..."}
                disabled={isLoading || isRecording}
                className="w-full h-12 px-4 bg-[--bg-elevated] border border-[--border] hover:border-[--border-strong] focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 rounded-xl text-[15px] text-[--text-primary] placeholder-[--text-muted] outline-none transition-all disabled:opacity-50"
              />
            </div>

            {/* Send button */}
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              className="w-12 h-12 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white flex items-center justify-center transition-colors disabled:opacity-30 disabled:hover:bg-emerald-500"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>

          {isRecording && (
            <div className="mt-3 flex items-center justify-center gap-2 text-red-400 text-sm">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              Recording... speak now, then tap stop
            </div>
          )}

          <p className="text-center text-xs text-[--text-muted] mt-3">
            Daktari is an AI assistant. Always consult a healthcare provider for medical advice.
          </p>
        </div>
      </div>
    </div>
  )
}

export default App

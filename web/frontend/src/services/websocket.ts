/**
 * WebSocket Service for yice real-time communication
 * 
 * Provides connection management, message sending, and event listening
 * for both agent dialogue and divination pipeline streaming.
 */

// Message types for agent dialogue (/ws/agent)
export interface AgentMessage {
  type: 'user_message' | 'assistant_chunk' | 'assistant_complete' | 'dialogue_complete' | 'error' | 'ping' | 'pong'
  content?: string
  options?: string[]
  message?: string
  question_context?: {
    raw_question: string
    question_type?: string
  }
}

// Message types for divination pipeline (/ws/divination)
export interface DivinationMessage {
  type: 'start_divination' | 'yao_start' | 'yao_thinking' | 'yao_complete' | 'all_complete' | 'error' | 'ping' | 'pong' | 'stage_start' | 'stage_complete' | 'hexagram_matched'
  position?: number
  line_name?: string
  yao_ci?: string
  analysis?: string
  advice?: string
  risks?: string
  stage?: 'qigua' | 'router' | 'yao' | 'reporter'
  hexagram_name?: string
  report?: DecisionReport
  message?: string
  status?: string
  question_context?: {
    raw_question: string
    question_type?: string
    background?: string
    constraints?: string
    expected_outcome?: string
    time_horizon?: string
    risk_tolerance?: string
  }
}

export interface DecisionReport {
  question: {
    raw_question: string
  }
  overall_advice: string
  key_risks: string
  timing_judgment: string
  next_steps: string[]
}

// Union type for all WebSocket messages
export type WebSocketMessage = AgentMessage | DivinationMessage

// Event callback type
export type MessageCallback = (data: WebSocketMessage) => void
export type StateCallback = (connected: boolean) => void

// Connection state
export const ConnectionState = {
  DISCONNECTED: 'disconnected' as const,
  CONNECTING: 'connecting' as const,
  CONNECTED: 'connected' as const,
  RECONNECTING: 'reconnecting' as const,
}

export type ConnectionState = typeof ConnectionState[keyof typeof ConnectionState]

export interface WebSocketServiceConfig {
  /** Base URL for WebSocket connection */
  baseUrl?: string
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean
  /** Maximum reconnect attempts */
  maxReconnectAttempts?: number
  /** Reconnect delay in milliseconds */
  reconnectDelay?: number
  /** Heartbeat interval in milliseconds */
  heartbeatInterval?: number
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private config: Required<WebSocketServiceConfig>
  private state: ConnectionState = ConnectionState.DISCONNECTED
  private reconnectAttempts = 0
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private messageCallbacks: Set<MessageCallback> = new Set()
  private stateCallbacks: Set<StateCallback> = new Set()
  private endpoint: 'agent' | 'divination' | null = null

  constructor(config: WebSocketServiceConfig = {}) {
    const isDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    // Use relative path for WebSocket to leverage Vite proxy
    const defaultUrl = isDev 
      ? `ws://${window.location.host}/ws`
      : `wss://${window.location.host}/ws`
    
    this.config = {
      baseUrl: config.baseUrl ?? defaultUrl,
      autoReconnect: config.autoReconnect ?? true,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 5,
      reconnectDelay: config.reconnectDelay ?? 3000,
      heartbeatInterval: config.heartbeatInterval ?? 30000,
    }
  }

  /**
   * Connect to WebSocket endpoint
   * @param endpoint - 'agent' for 起卦对话，'divination' for 推演流程
   */
  connect(endpoint: 'agent' | 'divination'): void {
    if (this.state === ConnectionState.CONNECTED || this.state === ConnectionState.CONNECTING) {
      console.warn('WebSocket already connected or connecting')
      return
    }

    this.endpoint = endpoint
    this.setState(ConnectionState.CONNECTING)

    const url = `${this.config.baseUrl}/${endpoint}`
    console.log(`Connecting to WebSocket: ${url}`)

    try {
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.setState(ConnectionState.CONNECTED)
        this.reconnectAttempts = 0
        this.startHeartbeat()
      }

      this.ws.onmessage = (event) => {
        try {
          console.log('Raw WebSocket data:', event.data)
          console.log('Data type:', typeof event.data)
          const data = JSON.parse(event.data) as WebSocketMessage
          console.log('Parsed data:', data)
          this.handleMessage(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
          console.error('Raw data:', event.data)
        }
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.stopHeartbeat()
        this.setState(ConnectionState.DISCONNECTED)

        if (this.config.autoReconnect && this.endpoint) {
          this.attemptReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      this.setState(ConnectionState.DISCONNECTED)
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.config.autoReconnect = false // Disable auto-reconnect on manual disconnect

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.stopHeartbeat()
    this.setState(ConnectionState.DISCONNECTED)
    this.endpoint = null
  }

  /**
   * Send message to WebSocket
   * @param message - Message object to send
   */
  sendMessage(message: AgentMessage | DivinationMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected')
      return
    }

    try {
      const data = JSON.stringify(message)
      this.ws.send(data)
    } catch (error) {
      console.error('Failed to send message:', error)
    }
  }

  /**
   * Send user message to agent endpoint
   * @param content - User message content
   */
  sendAgentMessage(content: string): void {
    if (this.endpoint !== 'agent') {
      console.error('Not connected to agent endpoint')
      return
    }

    this.sendMessage({
      type: 'user_message',
      content,
    })
  }

  /**
   * Start divination pipeline
   * @param questionContext - Question context object
   */
  startDivination(questionContext: {
    raw_question: string
    question_type?: string
    background?: string
    constraints?: string
    expected_outcome?: string
    time_horizon?: string
    risk_tolerance?: string
  }): void {
    if (this.endpoint !== 'divination') {
      console.error('Not connected to divination endpoint')
      return
    }

    this.sendMessage({
      type: 'start_divination',
      question_context: questionContext,
    })
  }

  /**
   * Register message callback
   * @param callback - Function to call on message received
   * @returns Unsubscribe function
   */
  onMessage(callback: MessageCallback): () => void {
    this.messageCallbacks.add(callback)

    return () => {
      this.messageCallbacks.delete(callback)
    }
  }

  /**
   * Register state change callback
   * @param callback - Function to call on state change
   * @returns Unsubscribe function
   */
  onStateChange(callback: StateCallback): () => void {
    this.stateCallbacks.add(callback)

    return () => {
      this.stateCallbacks.delete(callback)
    }
  }

  /**
   * Get current connection state
   */
  getState(): ConnectionState {
    return this.state
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.state === ConnectionState.CONNECTED
  }

  /**
   * Get current endpoint
   */
  getEndpoint(): 'agent' | 'divination' | null {
    return this.endpoint
  }

  private setState(state: ConnectionState): void {
    this.state = state
    this.stateCallbacks.forEach((callback) => callback(state === ConnectionState.CONNECTED))
  }

  private handleMessage(data: WebSocketMessage): void {
    // Handle pong response
    if (data.type === 'pong') {
      return
    }

    // Handle error messages
    if (data.type === 'error') {
      console.error('WebSocket error message:', data.message)
    }

    // Notify all callbacks
    this.messageCallbacks.forEach((callback) => callback(data))
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    this.setState(ConnectionState.RECONNECTING)

    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.config.maxReconnectAttempts})...`)

    setTimeout(() => {
      if (this.endpoint) {
        this.connect(this.endpoint)
      }
    }, this.config.reconnectDelay)
  }

  private startHeartbeat(): void {
    this.stopHeartbeat() // Clear any existing timer

    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendMessage({ type: 'ping' } as WebSocketMessage)
      }
    }, this.config.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }
}

// Export singleton instance for convenience
export const websocketService = new WebSocketService()

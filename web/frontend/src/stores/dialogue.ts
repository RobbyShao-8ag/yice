import { defineStore } from 'pinia'
import { websocketService, type AgentMessage } from '../services/websocket'

export interface Message {
  role: 'user' | 'assistant'
  content: string
  options?: string[]
}

interface DialogueState {
  messages: Message[]
  isComplete: boolean
  isLoading: boolean
  questionContext: {
    raw_question: string
    question_type?: string
    background?: string
    constraints?: string
    expected_outcome?: string
    time_horizon?: string
    risk_tolerance?: string
  } | null
}

export const useDialogueStore = defineStore('dialogue', {
  state: (): DialogueState => ({
    messages: [],
    isComplete: false,
    isLoading: false,
    questionContext: null,
  }),

  getters: {
    lastMessage: (state) => state.messages[state.messages.length - 1],
    hasMessages: (state) => state.messages.length > 0,
  },

  actions: {
    sendMessage(content: string) {
      if (websocketService.isConnected() && websocketService.getEndpoint() === 'agent') {
        websocketService.sendAgentMessage(content)
        this.addMessage({
          role: 'user',
          content,
        })
      } else {
        console.error('WebSocket not connected to agent endpoint')
      }
    },

    addMessage(message: Message) {
      this.messages.push(message)
    },

    setComplete() {
      this.isComplete = true
      this.isLoading = false
    },

    reset() {
      this.messages = []
      this.isComplete = false
      this.isLoading = false
    },

    setLoading(loading: boolean) {
      this.isLoading = loading
    },

    setQuestionContext(context: {
      raw_question: string
      question_type?: string
      background?: string
      constraints?: string
      expected_outcome?: string
      time_horizon?: string
      risk_tolerance?: string
    }) {
      this.questionContext = context
    },

    getQuestionContext() {
      return this.questionContext
    },

    handleAgentMessage(data: AgentMessage) {
      switch (data.type) {
        case 'assistant_chunk':
          if (data.content) {
            this.addMessage({
              role: 'assistant',
              content: data.content,
              options: data.options,
            })
          }
          break
        case 'assistant_complete':
          this.isLoading = false
          this.setComplete()
          break
        case 'dialogue_complete':
          this.setComplete()
          if ('question_context' in data && data.question_context) {
            this.setQuestionContext(data.question_context)
          }
          break
        case 'error':
          console.error('Agent error:', data.message)
          this.setLoading(false)
          break
      }
    },
  },
})

import { defineStore } from 'pinia'
import { websocketService, type DivinationMessage } from '../services/websocket'

export interface YaoOutput {
  position: number
  lineName: string
  yaoCi: string
  analysis: string
  advice: string
  risks?: string
}

export interface Report {
  question: {
    raw_question: string
  }
  overall_advice: string
  key_risks: string
  timing_judgment: string
  next_steps: string[]
  yao_summary?: {
    position: number
    line_name: string
    yao_ci: string
    brief: string
  }[]
}

interface DivinationState {
  isRunning: boolean
  currentYao: number
  outputs: YaoOutput[]
  report: Report | null
}

export const useDivinationStore = defineStore('divination', {
  state: (): DivinationState => ({
    isRunning: false,
    currentYao: 0,
    outputs: [],
    report: null,
  }),

  getters: {
    isComplete: (state) => state.outputs.length >= 6 && state.report !== null,
    currentProgress: (state) => state.outputs.length,
  },

  actions: {
    start(questionContext: {
      raw_question: string
      question_type?: string
      background?: string
      constraints?: string
      expected_outcome?: string
      time_horizon?: string
      risk_tolerance?: string
    }) {
      if (websocketService.isConnected() && websocketService.getEndpoint() === 'divination') {
        websocketService.startDivination(questionContext)
        this.reset()
        this.isRunning = true
      } else {
        console.error('WebSocket not connected to divination endpoint')
      }
    },

    addYaoOutput(output: YaoOutput) {
      this.outputs.push(output)
      this.currentYao = output.position
    },

    setReport(report: Report) {
      this.report = report
      this.isRunning = false
    },

    reset() {
      this.isRunning = false
      this.currentYao = 0
      this.outputs = []
      this.report = null
    },

    handleDivinationMessage(data: DivinationMessage) {
      switch (data.type) {
        case 'start_divination':
          this.isRunning = true
          break
        case 'yao_start':
          this.currentYao = data.position ?? 0
          break
        case 'yao_complete':
          if (data.position !== undefined) {
            this.addYaoOutput({
              position: data.position,
              lineName: data.line_name ?? '',
              yaoCi: data.yao_ci ?? '',
              analysis: data.analysis ?? '',
              advice: data.advice ?? '',
              risks: data.risks,
            })
          }
          break
        case 'all_complete':
          this.isRunning = false
          break
        case 'error':
          console.error('Divination error:', data.message)
          this.isRunning = false
          break
      }
    },
  },
})

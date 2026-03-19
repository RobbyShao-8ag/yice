import { defineStore } from 'pinia'

interface AppState {
  isConfigured: boolean
  isLoading: boolean
  error: string | null
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    isConfigured: false,
    isLoading: false,
    error: null,
  }),

  getters: {
    isReady: (state) => state.isConfigured && !state.isLoading,
  },

  actions: {
    checkConfig() {
      const stored = localStorage.getItem('yice_llm_config')
      this.isConfigured = stored !== null && stored.length > 0
      return this.isConfigured
    },
    setLoading(loading: boolean) {
      this.isLoading = loading
    },
    setError(error: string | null) {
      this.error = error
    },
    setConfigured(configured: boolean) {
      this.isConfigured = configured
    },
  },
})

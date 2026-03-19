<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'

interface ProviderConfig {
  api_key: string
  base_url: string
  default_model?: string
}

interface AgentConfig {
  provider: string
  model: string
}

interface ConfigData {
  providers: Record<string, ProviderConfig>
  agents: Record<string, AgentConfig>
}

interface TestResult {
  success: boolean
  message: string
}

// 固定智能体配置（中文显示名 -> 内部key映射）
const AGENT_DISPLAY_NAMES: Record<string, string> = {
  '起卦官': 'qigua_agent',
  '场景路由官': 'scene_router',
  '六爻推演官': 'yao_agent',
  '决策报告官': 'reporter'
}

const AGENT_DESCRIPTIONS: Record<string, string> = {
  '起卦官': '通过多轮对话收集用户决策信息',
  '场景路由官': '匹配最适合的卦象和场景',
  '六爻推演官': '分析六个爻位的吉凶变化',
  '决策报告官': '生成最终的决策参考报告'
}

const loading = ref(false)
const saving = ref(false)
const testing = ref<Record<string, boolean>>({})
const testResults = ref<Record<string, TestResult>>({})
const config = reactive<ConfigData>({
  providers: {},
  agents: {},
})

// 添加新的 provider
const newProviderName = ref('')
const newProviderUrl = ref('https://api.openai.com')
const newProviderModel = ref('gpt-3.5-turbo')

// 计算属性：获取所有智能体的中文显示名
const agentDisplayNames = computed(() => Object.keys(AGENT_DISPLAY_NAMES))

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  loading.value = true
  try {
    const res = await fetch('/api/config/')
    const data = await res.json()
    
    if (data.status === 'ok') {
      // 清空现有配置
      Object.keys(config.providers).forEach(key => delete config.providers[key])
      Object.keys(config.agents).forEach(key => delete config.agents[key])
      
      // 加载配置
      if (data.config.providers) {
        Object.assign(config.providers, data.config.providers)
      }
      if (data.config.agents) {
        Object.assign(config.agents, data.config.agents)
      }
      
      // 确保4个固定智能体都存在
      ensureFixedAgents()
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  } finally {
    loading.value = false
  }
}

// 确保4个固定智能体都存在
function ensureFixedAgents() {
  const defaultProvider = Object.keys(config.providers)[0] || ''
  const defaultModel = defaultProvider ? config.providers[defaultProvider].default_model || '' : ''
  
  Object.values(AGENT_DISPLAY_NAMES).forEach((key) => {
    if (!config.agents[key]) {
      config.agents[key] = {
        provider: defaultProvider,
        model: defaultModel
      }
    }
  })
}

async function saveConfig() {
  saving.value = true
  try {
    const res = await fetch('/api/config/', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    
    const data = await res.json()
    
    if (res.ok && data.status === 'ok') {
      alert('配置已保存')
      testResults.value = {} // 清空测试结果
    } else {
      alert(`保存失败：${data.detail || '未知错误'}`)
    }
  } catch (error) {
    console.error('保存配置失败:', error)
    alert('保存失败：网络错误')
  } finally {
    saving.value = false
  }
}

async function testConnection(providerName: string) {
  const provider = config.providers[providerName]
  if (!provider) return
  
  testing.value[providerName] = true
  testResults.value[providerName] = { success: false, message: '测试中...' }
  
  try {
    const params = new URLSearchParams({
      provider_name: providerName,
      model: provider.default_model || '',
      api_key: provider.api_key,
      base_url: provider.base_url,
    })
    
    const res = await fetch(`/api/config/test?${params}`, {
      method: 'POST',
    })
    
    const data = await res.json()
    
    if (res.ok && data.status === 'ok') {
      testResults.value[providerName] = {
        success: true,
        message: '连接成功！' + (data.response ? ` 响应：${data.response}` : ''),
      }
    } else {
      testResults.value[providerName] = {
        success: false,
        message: data.detail || '测试失败',
      }
    }
  } catch (error) {
    console.error('测试连接失败:', error)
    testResults.value[providerName] = {
      success: false,
      message: '网络错误',
    }
  } finally {
    testing.value[providerName] = false
  }
}

function addProvider() {
  if (!newProviderName.value.trim()) {
    alert('请输入服务商名称')
    return
  }
  
  if (config.providers[newProviderName.value]) {
    alert('服务商已存在')
    return
  }
  
  config.providers[newProviderName.value] = {
    api_key: '',
    base_url: newProviderUrl.value,
    default_model: newProviderModel.value,
  }
  
  newProviderName.value = ''
  
  // 如果有新provider，更新智能体的默认值
  ensureFixedAgents()
}

function removeProvider(name: string) {
  // 检查是否有 agent 使用此 provider
  const usedByAgent = Object.entries(config.agents).some(
    ([, agent]) => agent.provider === name
  )
  
  if (usedByAgent) {
    alert(`无法删除：有智能体正在使用此服务商`)
    return
  }
  
  if (confirm(`确定要删除服务商 "${name}" 吗？`)) {
    delete config.providers[name]
    delete testResults.value[name]
  }
}

function updateAgentModel(agentKey: string, model: string) {
  if (config.agents[agentKey]) {
    config.agents[agentKey].model = model
  }
}

function updateAgentProvider(agentKey: string, providerName: string) {
  if (config.agents[agentKey]) {
    config.agents[agentKey].provider = providerName
    // 同步更新模型为provider的默认模型
    if (config.providers[providerName]?.default_model) {
      config.agents[agentKey].model = config.providers[providerName].default_model
    }
  }
}
</script>

<template>
  <div class="settings-view">
    <div class="settings-container">
      <h1 class="page-title">⚙️ 系统配置</h1>
      
      <div v-if="loading" class="loading-state">
        <span class="loading-spinner">⏳</span>
        <p>加载配置中...</p>
      </div>
      
      <div v-else class="settings-content">
        <!-- 左右布局 -->
        <div class="settings-grid">
          <!-- 左侧：服务商配置 -->
          <section class="settings-section">
            <h2 class="section-title">🤖 模型服务商</h2>
            <p class="section-desc">配置大语言模型 API 连接信息</p>
            
            <div class="provider-list">
              <div v-for="(provider, name) in config.providers" :key="name" class="provider-card">
                <div class="provider-header">
                  <h3 class="provider-name">{{ name }}</h3>
                  <button class="btn-icon btn-danger" @click="removeProvider(name)" title="删除">🗑️</button>
                </div>
                
                <div class="form-row">
                  <div class="form-group flex-2">
                    <label class="form-label">API 密钥</label>
                    <input
                      v-model="provider.api_key"
                      type="password"
                      class="form-input"
                      placeholder="sk-..."
                      autocomplete="off"
                    />
                  </div>
                  <div class="form-group flex-2">
                    <label class="form-label">API 地址</label>
                    <input
                      v-model="provider.base_url"
                      type="url"
                      class="form-input"
                      placeholder="https://api.openai.com"
                    />
                  </div>
                  <div class="form-group flex-1">
                    <label class="form-label">默认模型</label>
                    <input
                      v-model="provider.default_model"
                      type="text"
                      class="form-input"
                      placeholder="gpt-3.5-turbo"
                    />
                  </div>
                </div>
                
                <div class="provider-actions">
                  <button
                    class="btn btn-sm btn-primary"
                    :disabled="testing[name]"
                    @click="testConnection(name)"
                  >
                    {{ testing[name] ? '测试中...' : '测试连接' }}
                  </button>
                  
                  <div v-if="testResults[name]" :class="['test-result', testResults[name].success ? 'success' : 'error']">
                    {{ testResults[name].message }}
                  </div>
                </div>
              </div>
              
              <!-- 添加新 Provider -->
              <div class="provider-card add-card">
                <h3 class="provider-name">➕ 添加服务商</h3>
                <div class="form-row">
                  <div class="form-group">
                    <input
                      v-model="newProviderName"
                      type="text"
                      class="form-input"
                      placeholder="名称 (如：openai)"
                    />
                  </div>
                  <div class="form-group">
                    <input
                      v-model="newProviderUrl"
                      type="url"
                      class="form-input"
                      placeholder="API 地址"
                    />
                  </div>
                  <div class="form-group">
                    <input
                      v-model="newProviderModel"
                      type="text"
                      class="form-input"
                      placeholder="默认模型"
                    />
                  </div>
                  <button class="btn btn-sm btn-secondary" @click="addProvider">添加</button>
                </div>
              </div>
            </div>
          </section>
          
          <!-- 右侧：智能体配置 -->
          <section class="settings-section">
            <h2 class="section-title">🔧 智能体配置</h2>
            <p class="section-desc">为4个固定智能体分配模型服务商</p>
            
            <div class="agent-list">
              <div 
                v-for="displayName in agentDisplayNames" 
                :key="displayName" 
                class="agent-card"
              >
                <div class="agent-info">
                  <h3 class="agent-name">{{ displayName }}</h3>
                  <p class="agent-desc">{{ AGENT_DESCRIPTIONS[displayName] }}</p>
                </div>
                
                <div class="agent-config">
                  <div class="form-group">
                    <label class="form-label">服务商</label>
                    <select
                      :value="config.agents[AGENT_DISPLAY_NAMES[displayName]]?.provider || ''"
                      class="form-select"
                      @change="updateAgentProvider(AGENT_DISPLAY_NAMES[displayName], ($event.target as HTMLSelectElement).value)"
                    >
                      <option value="">请选择</option>
                      <option v-for="provider in Object.keys(config.providers)" :key="provider" :value="provider">
                        {{ provider }}
                      </option>
                    </select>
                  </div>
                  
                  <div class="form-group">
                    <label class="form-label">模型</label>
                    <input
                      :value="config.agents[AGENT_DISPLAY_NAMES[displayName]]?.model || ''"
                      type="text"
                      class="form-input"
                      placeholder="模型名称"
                      @input="updateAgentModel(AGENT_DISPLAY_NAMES[displayName], ($event.target as HTMLInputElement).value)"
                    />
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
        
        <!-- 保存按钮 -->
        <div class="save-actions">
          <button
            class="btn btn-primary btn-large"
            :disabled="saving"
            @click="saveConfig"
          >
            {{ saving ? '保存中...' : '💾 保存配置' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  min-height: calc(100vh - 73px);
  background-color: var(--bg-color);
  padding: 24px 20px;
}

.settings-container {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  color: var(--text-primary);
  font-family: var(--font-serif);
  letter-spacing: 4px;
  margin-bottom: 24px;
  text-align: center;
}

.loading-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 28px;
  display: block;
  margin-bottom: 12px;
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 左右布局网格 */
.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 1200px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}

.settings-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 20px;
}

.section-title {
  font-size: 16px;
  color: var(--text-primary);
  font-family: var(--font-serif);
  letter-spacing: 2px;
  margin-bottom: 4px;
}

.section-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

/* Provider 列表 */
.provider-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.provider-card {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
}

.provider-card.add-card {
  border-style: dashed;
  border-width: 2px;
}

.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.provider-name {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 600;
  margin: 0;
}

.form-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.form-group {
  margin-bottom: 8px;
}

.form-group.flex-1 {
  flex: 1;
}

.form-group.flex-2 {
  flex: 2;
}

.form-label {
  display: block;
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 3px;
  font-weight: 500;
}

.form-input,
.form-select {
  width: 100%;
  padding: 6px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 12px;
  transition: border-color 0.2s;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--accent-color);
}

.form-select {
  cursor: pointer;
}

.provider-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color);
}

.test-result {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  flex: 1;
}

.test-result.success {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.test-result.error {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Agent 列表 */
.agent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-card {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
  display: flex;
  gap: 16px;
  align-items: center;
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 600;
  margin: 0 0 3px 0;
}

.agent-desc {
  font-size: 11px;
  color: var(--text-secondary);
  margin: 0;
}

.agent-config {
  display: flex;
  gap: 10px;
  flex: 1.5;
}

.agent-config .form-group {
  flex: 1;
  margin-bottom: 0;
}

/* 按钮样式 */
.btn {
  padding: 6px 14px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: 5px 12px;
  font-size: 11px;
}

.btn-primary {
  background: var(--accent-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-secondary {
  background: var(--bg-hover);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--border-color);
}

.btn-large {
  padding: 10px 28px;
  font-size: 14px;
}

.btn-icon {
  background: none;
  border: none;
  font-size: 14px;
  cursor: pointer;
  padding: 2px;
  border-radius: 3px;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: var(--bg-hover);
}

.btn-danger:hover {
  background: rgba(239, 68, 68, 0.15);
}

/* 保存按钮 */
.save-actions {
  display: flex;
  justify-content: center;
  padding: 10px;
}
</style>

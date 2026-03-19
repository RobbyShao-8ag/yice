<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface HistoryItem {
  id: string
  filename: string
  question: string
  hexagram: string
  created_at: string
}

interface HistoryDetail {
  id: string
  content: {
    question: string
    hexagram: {
      name: string
      description?: string
    }
    yao_analysis: Array<{
      position: number
      line_name: string
      analysis: string
      advice: string
    }>
    report: {
      overall_advice: string
      key_risks: string
      timing_judgment: string
      next_steps: string[]
    }
  }
  created_at: string
}

const loading = ref(false)
const historyList = ref<HistoryItem[]>([])
const selectedRecord = ref<HistoryDetail | null>(null)
const viewingDetail = ref(false)
const deleting = ref(false)

onMounted(async () => {
  await loadHistory()
})

async function loadHistory() {
  loading.value = true
  try {
    const res = await fetch('/api/history/')
    const data = await res.json()
    historyList.value = data.history || []
  } catch (error) {
    console.error('加载历史记录失败:', error)
  } finally {
    loading.value = false
  }
}

async function viewDetail(id: string) {
  loading.value = true
  try {
    const res = await fetch(`/api/history/${id}`)
    const data = await res.json()
    
    if (res.ok) {
      selectedRecord.value = data
      viewingDetail.value = true
    } else {
      alert(`加载失败：${data.detail || '未知错误'}`)
    }
  } catch (error) {
    console.error('加载历史记录失败:', error)
    alert('加载失败：网络错误')
  } finally {
    loading.value = false
  }
}

async function deleteRecord(id: string, index: number) {
  if (!confirm('确定要删除这条历史记录吗？此操作不可恢复。')) {
    return
  }
  
  deleting.value = true
  try {
    const res = await fetch(`/api/history/${id}`, {
      method: 'DELETE',
    })
    
    const data = await res.json()
    
    if (res.ok) {
      historyList.value.splice(index, 1)
      if (selectedRecord.value?.id === id) {
        viewingDetail.value = false
        selectedRecord.value = null
      }
      alert('已删除')
    } else {
      alert(`删除失败：${data.detail || '未知错误'}`)
    }
  } catch (error) {
    console.error('删除历史记录失败:', error)
    alert('删除失败：网络错误')
  } finally {
    deleting.value = false
  }
}

  viewingDetail.value = false
  selectedRecord.value = null
function formatDate(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function goBack() {
  viewingDetail.value = false
  selectedRecord.value = null
}
</script>

<template>
  <div class="history-view">
    <div class="history-container">
      <h1 class="page-title">📜 历史记录</h1>
      
      <div v-if="loading && !viewingDetail" class="loading-state">
        <span class="loading-spinner">⏳</span>
        <p>加载历史记录中...</p>
      </div>
      
      <!-- 历史记录列表 -->
      <div v-else-if="!viewingDetail" class="history-list-wrapper">
        <div v-if="historyList.length === 0" class="empty-state">
          <span class="empty-icon">📭</span>
          <p class="empty-text">暂无历史记录</p>
          <p class="empty-desc">进行一次占卜后，记录会显示在这里</p>
        </div>
        
        <div v-else class="history-list">
          <div
            v-for="(item, index) in historyList"
            :key="item.id"
            class="history-card"
          >
            <div class="history-header">
              <div class="history-meta">
                <h3 class="history-question">{{ item.question || '未命名问题' }}</h3>
                <div class="history-info">
                  <span class="history-hexagram" v-if="item.hexagram">
                    卦象：{{ item.hexagram }}
                  </span>
                  <span class="history-time">
                    {{ formatDate(item.created_at) }}
                  </span>
                </div>
              </div>
              
              <div class="history-actions">
                <button
                  class="btn btn-primary"
                  @click="viewDetail(item.id)"
                  :disabled="loading"
                >
                  🔍 查看
                </button>
                <button
                  class="btn btn-danger"
                  @click="deleteRecord(item.id, index)"
                  :disabled="deleting"
                  title="删除"
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 历史记录详情 -->
      <div v-else-if="selectedRecord" class="history-detail">
        <div class="detail-header">
          <button class="btn btn-back" @click="goBack">
            ← 返回列表
          </button>
          <button
            class="btn btn-danger"
            @click="selectedRecord?.id && deleteRecord(selectedRecord.id, historyList.findIndex(h => h.id === selectedRecord?.id))"
            :disabled="deleting || !selectedRecord"
          >
            🗑️ 删除
          </button>
        </div>
        
        <div class="detail-content">
          <section class="detail-section">
            <h2 class="section-title">问题</h2>
            <p class="section-content">{{ selectedRecord.content.question }}</p>
          </section>
          
          <section class="detail-section">
            <h2 class="section-title">卦象</h2>
            <p class="section-content">
              <strong>{{ selectedRecord.content.hexagram.name }}</strong>
              <span v-if="selectedRecord.content.hexagram.description">
                - {{ selectedRecord.content.hexagram.description }}
              </span>
            </p>
          </section>
          
          <section class="detail-section">
            <h2 class="section-title">六爻分析</h2>
            <div class="yao-analysis">
              <div
                v-for="yao in selectedRecord.content.yao_analysis"
                :key="yao.position"
                class="yao-card"
              >
                <h4 class="yao-title">
                  {{ yao.line_name }} (第{{ yao.position }}爻)
                </h4>
                <div class="yao-content">
                  <div class="yao-item">
                    <span class="yao-label">分析:</span>
                    <p class="yao-text">{{ yao.analysis }}</p>
                  </div>
                  <div class="yao-item">
                    <span class="yao-label">建议:</span>
                    <p class="yao-text">{{ yao.advice }}</p>
                  </div>
                </div>
              </div>
            </div>
          </section>
          
          <section class="detail-section">
            <h2 class="section-title">决策建议</h2>
            <div class="report-content">
              <div class="report-item">
                <h4>总体建议</h4>
                <p>{{ selectedRecord.content.report.overall_advice }}</p>
              </div>
              <div class="report-item">
                <h4>关键风险</h4>
                <p>{{ selectedRecord.content.report.key_risks }}</p>
              </div>
              <div class="report-item">
                <h4>时机判断</h4>
                <p>{{ selectedRecord.content.report.timing_judgment }}</p>
              </div>
              <div class="report-item" v-if="selectedRecord.content.report.next_steps?.length">
                <h4>下一步行动</h4>
                <ul class="next-steps">
                  <li v-for="(step, idx) in selectedRecord.content.report.next_steps" :key="idx">
                    {{ step }}
                  </li>
                </ul>
              </div>
            </div>
          </section>
          
          <div class="detail-footer">
            <p class="created-time">
              创建时间：{{ formatDate(selectedRecord.created_at) }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-view {
  min-height: calc(100vh - 73px);
  background-color: var(--bg-color);
  padding: 40px 20px;
}

.history-container {
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  font-size: 28px;
  color: var(--text-primary);
  font-family: var(--font-serif);
  letter-spacing: 4px;
  margin-bottom: 32px;
  text-align: center;
}

.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 32px;
  display: block;
  margin-bottom: 16px;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 64px;
  display: block;
  margin-bottom: 24px;
  opacity: 0.6;
}

.empty-text {
  font-size: 18px;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.empty-desc {
  font-size: 14px;
}

.history-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.history-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.history-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.history-meta {
  flex: 1;
  min-width: 0;
}

.history-question {
  font-size: 18px;
  color: var(--text-primary);
  font-weight: 600;
  margin: 0 0 12px 0;
  word-break: break-word;
}

.history-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}

.history-hexagram {
  background: var(--bg-hover);
  padding: 4px 10px;
  border-radius: 4px;
}

.history-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--accent-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-danger {
  background: #fee2e2;
  color: #991b1b;
}

.btn-danger:hover:not(:disabled) {
  background: #fecaca;
}

.btn-back {
  background: var(--bg-hover);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-back:hover {
  background: var(--border-color);
}

/* 详情视图 */
.history-detail {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-hover);
}

.detail-content {
  padding: 32px 24px;
}

.detail-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 18px;
  color: var(--text-primary);
  font-family: var(--font-serif);
  letter-spacing: 2px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--accent-color);
}

.section-content {
  font-size: 15px;
  color: var(--text-primary);
  line-height: 1.7;
}

/* 六爻分析 */
.yao-analysis {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.yao-card {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
}

.yao-title {
  font-size: 16px;
  color: var(--text-primary);
  font-weight: 600;
  margin: 0 0 12px 0;
}

.yao-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.yao-item {
  display: flex;
  gap: 12px;
}

.yao-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  flex-shrink: 0;
  min-width: 50px;
}

.yao-text {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  margin: 0;
  flex: 1;
}

/* 决策报告 */
.report-content {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 24px;
}

.report-item {
  margin-bottom: 20px;
}

.report-item:last-child {
  margin-bottom: 0;
}

.report-item h4 {
  font-size: 15px;
  color: var(--text-primary);
  font-weight: 600;
  margin-bottom: 8px;
}

.report-item p {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.7;
  margin: 0;
}

.next-steps {
  list-style: none;
  padding: 0;
  margin: 0;
}

.next-steps li {
  font-size: 14px;
  color: var(--text-primary);
  padding: 6px 0 6px 20px;
  position: relative;
  line-height: 1.6;
}

.next-steps li::before {
  content: '→';
  position: absolute;
  left: 0;
  color: var(--accent-color);
}

.detail-footer {
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
  text-align: center;
}

.created-time {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

@media (max-width: 640px) {
  .history-header {
    flex-direction: column;
  }
  
  .history-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>

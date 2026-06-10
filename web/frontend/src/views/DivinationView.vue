<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDivinationStore } from '../stores/divination'
import { useDialogueStore } from '../stores/dialogue'
import { websocketService, type WebSocketMessage, type DivinationMessage } from '../services/websocket'
import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true
})

// Helper function to render Markdown
const renderMarkdown = (text: string): string => {
  if (!text || text === '待补充') return ''
  return marked.parse(text) as string
}

// Helper function to check if content is meaningful
const hasContent = (text: string | undefined | null): boolean => {
  if (!text) return false
  const trimmed = text.trim()
  return trimmed !== '' && trimmed !== '待补充' && trimmed !== '待生成建议' && trimmed !== '待风险评估'
}

const formatYaoCi = (text: string): string => {
  if (!text) return ''
  const withoutWilhelm = text.split('【Wilhelm解读】')[0].trim()
  const normalized = withoutWilhelm
    .split(/\n+/)
    .map(line => line.trim())
    .filter(Boolean)
    .join(' ')
  return normalized.length > 80 ? `${normalized.slice(0, 80).trim()}...` : normalized
}

const router = useRouter()

// 六爻数据结构（用于图形显示）
interface YaoData {
  position: string
  name: string
  type: 'yang' | 'yin'
  text: string
  interpretation: string
  advice: string
}

// 组件状态
const isRunning = ref(false)
const currentYaoIndex = ref(-1)
const statusText = ref('等待开始推演')
const activeYaoPositions = ref<Set<number>>(new Set())
const completedYaoPositions = ref<Set<number>>(new Set())
const showReportModal = ref(false)
const hexagramName = ref('')
const finalReport = ref<{
  overall_advice: string
  key_risks: string | string[]
  timing_judgment: string
  next_steps: string[]
  yao_summary?: {
    position: number
    line_name: string
    yao_ci: string
    brief: string
  }[]
} | null>(null)

const keyRisksList = computed(() => {
  if (!finalReport.value?.key_risks) return []
  const risks = finalReport.value.key_risks
  if (Array.isArray(risks)) return risks
  return risks.split(/[；;。\n]/).filter((s: string) => s.trim())
})

// Pinia Store
const divinationStore = useDivinationStore()
const dialogueStore = useDialogueStore()

// 计算属性：从 Store 获取输出
const outputs = computed(() => divinationStore.outputs)
const completedYaoCount = computed(() => completedYaoPositions.value.size)
const pendingYaoCount = computed(() => Math.max(activeYaoPositions.value.size - completedYaoPositions.value.size, 0))
const progressText = computed(() => {
  if (!isRunning.value) return statusText.value
  if (activeYaoPositions.value.size > 0) {
    return `六爻并行推演中：已完成 ${completedYaoCount.value}/${activeYaoPositions.value.size}，剩余 ${pendingYaoCount.value} 爻`
  }
  return statusText.value
})
const isYaoCompleted = (position: number): boolean => completedYaoPositions.value.has(position)

// 六爻圆环尺寸（由内到外，单位：px）
const ringSizes = [120, 175, 230, 285, 340, 395]

// 六爻颜色配置（由内到外）
const yaoColors = [
  { color: 'var(--yao-1-color)', glow: 'var(--glow-yao-1)' },
  { color: 'var(--yao-2-color)', glow: 'var(--glow-yao-2)' },
  { color: 'var(--yao-3-color)', glow: 'var(--glow-yao-3)' },
  { color: 'var(--yao-4-color)', glow: 'var(--glow-yao-4)' },
  { color: 'var(--yao-5-color)', glow: 'var(--glow-yao-5)' },
  { color: 'var(--yao-6-color)', glow: 'var(--glow-yao-6)' }
]

// Mock 六爻数据（仅用于图形显示，实际数据来自 WebSocket）
const yaoDataList: YaoData[] = [
  {
    position: '初爻',
    name: '环境感知',
    type: 'yang',
    text: '潜龙勿用',
    interpretation: '当前处于积累潜伏期，宜静心修炼内功',
    advice: '不宜冒进，继续沉淀'
  },
  {
    position: '二爻',
    name: '资源配置',
    type: 'yin',
    text: '见龙在田，利见大人',
    interpretation: '时机逐渐成熟，可寻求贵人相助',
    advice: '把握时机，适度展现才能'
  },
  {
    position: '三爻',
    name: '风险评估',
    type: 'yang',
    text: '君子终日乾乾，夕惕若厉',
    interpretation: '处于关键转折点，需要谨慎行事',
    advice: '保持警觉，稳扎稳打'
  },
  {
    position: '四爻',
    name: '策略执行',
    type: 'yin',
    text: '或跃在渊，无咎',
    interpretation: '进退维谷之际，需审时度势',
    advice: '灵活应变，不宜固执'
  },
  {
    position: '五爻',
    name: '长期规划',
    type: 'yang',
    text: '飞龙在天，利见大人',
    interpretation: '大势已成，正是展翅高飞之时',
    advice: '把握大局，乘势而为'
  },
  {
    position: '上爻',
    name: '结果复盘',
    type: 'yang',
    text: '亢龙有悔',
    interpretation: '盛极而衰，需知进退之道',
    advice: '居安思危，留有余地'
  }
]

// 处理 WebSocket 消息
const handleDivinationMessage = (data: WebSocketMessage) => {
  // 只处理 divination 相关消息
  if (data.type === 'user_message' || data.type === 'assistant_chunk' || 
      data.type === 'assistant_complete' || data.type === 'dialogue_complete') {
    return
  }
  
  const divinationData = data as DivinationMessage
  console.log('Divination message:', divinationData)
  
  switch (divinationData.type) {
    case 'stage_start':
      statusText.value = divinationData.message || '正在推演...'
      break
    case 'hexagram_matched':
      hexagramName.value = divinationData.hexagram_name || ''
      statusText.value = `已匹配卦象：${divinationData.hexagram_name}`
      break
    case 'yao_start':
      if (divinationData.position !== undefined) {
        activeYaoPositions.value = new Set([...activeYaoPositions.value, divinationData.position])
        statusText.value = '六爻并行推演中...'
      }
      break
    case 'yao_thinking':
      // 思考中，可以显示加载状态
      break
    case 'yao_complete':
      if (divinationData.position !== undefined) {
        completedYaoPositions.value = new Set([...completedYaoPositions.value, divinationData.position])
        divinationStore.addYaoOutput({
          position: divinationData.position,
          lineName: divinationData.line_name || '',
          yaoCi: formatYaoCi(divinationData.yao_ci || ''),
          analysis: divinationData.analysis || '',
          advice: divinationData.advice || '',
          risks: divinationData.risks || '',
        })
        currentYaoIndex.value = Math.max(currentYaoIndex.value, divinationData.position)
        statusText.value = progressText.value
      }
      break
    case 'stage_complete':
      statusText.value = divinationData.message || '阶段完成'
      break
    case 'all_complete':
      isRunning.value = false
      statusText.value = '推演完成'
      if (divinationData.report) {
        finalReport.value = {
          overall_advice: divinationData.report.overall_advice,
          key_risks: divinationData.report.key_risks,
          timing_judgment: divinationData.report.timing_judgment,
          next_steps: divinationData.report.next_steps,
          yao_summary: divinationData.report.yao_summary,
        }
        showReportModal.value = true
      }
      break
    case 'error':
      isRunning.value = false
      statusText.value = '推演出错'
      console.error('Divination error:', divinationData.message)
      break
  }
}

// 开始推演
const startDivination = () => {
  if (isRunning.value) return
  
  // 获取 question context
  const questionContext = dialogueStore.getQuestionContext()
  if (!questionContext) {
    alert('请先完成起卦对话')
    return
  }
  
  // 确保先断开 agent 连接，再连接 divination
  if (websocketService.isConnected()) {
    websocketService.disconnect()
  }
  
  // 连接到 divination WebSocket
  websocketService.connect('divination')
  
  // 等待连接成功后发送开始请求
  setTimeout(() => {
    if (websocketService.isConnected()) {
      divinationStore.start(questionContext)
      isRunning.value = true
      currentYaoIndex.value = -1
      activeYaoPositions.value = new Set()
      completedYaoPositions.value = new Set()
      statusText.value = '开始推演...'
    } else {
      console.error('Failed to connect to divination endpoint')
      alert('连接推演服务失败，请重试')
    }
  }, 500)
}

// 关闭报告弹窗
const closeReportModal = () => {
  showReportModal.value = false
}

// 重新开始 - 清空记录，返回起卦界面
const restartDivination = () => {
  dialogueStore.reset()
  divinationStore.reset()
  websocketService.disconnect()
  router.push('/')
}

// 复制输出
const copyOutput = () => {
  // TODO: 实现复制功能
  alert('复制功能开发中')
}

// 导出输出
const exportOutput = () => {
  // TODO: 实现导出功能
  alert('导出功能开发中')
}

// 组件挂载时注册消息处理
onMounted(() => {
  websocketService.onMessage(handleDivinationMessage)
  // 如果对话已完成，自动开始推演
  if (dialogueStore.isComplete && !isRunning.value && outputs.value.length === 0) {
    // 延迟一点，确保 WebSocket 连接建立
    setTimeout(() => {
      startDivination()
    }, 500)
  }
})

// 组件卸载时断开 WebSocket
onUnmounted(() => {
  websocketService.disconnect()
})
</script>

<template>
  <div class="divination-view">
    <!-- 左侧图形区域 -->
    <section class="graphics-section">
      <!-- 算卦舞台 -->
      <div class="divination-stage">
        <!-- 八卦方位 -->
        <div class="bagua-directions">
          <span class="bagua-char qian">乾·南</span>
          <span class="bagua-char kun">坤·北</span>
          <span class="bagua-char zhen">震·东北</span>
          <span class="bagua-char xun">巽·东南</span>
          <span class="bagua-char kan">坎·西北</span>
          <span class="bagua-char li">离·西南</span>
          <span class="bagua-char gen">艮·东</span>
          <span class="bagua-char dui">兑·西</span>
        </div>

        <!-- 六爻同心圆 -->
        <div class="yao-rings-container">
          <div
            v-for="(size, index) in ringSizes"
            :key="index"
            class="yao-ring"
            :class="[
              `yao-ring-${index + 1}`,
              { active: isYaoCompleted(index + 1) }
            ]"
            :style="{
              width: `${size}px`,
              height: `${size}px`,
              borderColor: isYaoCompleted(index + 1)
                ? yaoColors[index].color
                : 'rgba(255, 255, 255, 0.08)',
              boxShadow: isYaoCompleted(index + 1)
                ? `0 0 30px ${yaoColors[index].glow}, inset 0 0 30px ${yaoColors[index].glow}`
                : 'none'
            }"
          >
            <!-- 爻线 SVG -->
            <svg class="yao-svg" :viewBox="`0 0 ${size} ${size}`">
              <!-- 阳爻：一条长线 -->
              <line
                v-if="yaoDataList[index]?.type === 'yang'"
                class="yao-line"
                :class="{ yang: isYaoCompleted(index + 1) }"
                :x1="size * 0.25"
                :y1="size / 2"
                :x2="size * 0.75"
                :y2="size / 2"
                :stroke="isYaoCompleted(index + 1) ? yaoColors[index].color : 'rgba(255, 255, 255, 0.1)'"
              />
              <!-- 阴爻：两条短线 -->
              <g v-else>
                <line
                  class="yao-line"
                  :class="{ yin: isYaoCompleted(index + 1) }"
                  :x1="size * 0.15"
                  :y1="size / 2"
                  :x2="size * 0.45"
                  :y2="size / 2"
                  :stroke="isYaoCompleted(index + 1) ? yaoColors[index].color : 'rgba(255, 255, 255, 0.1)'"
                />
                <line
                  class="yao-line"
                  :class="{ yin: isYaoCompleted(index + 1) }"
                  :x1="size * 0.55"
                  :y1="size / 2"
                  :x2="size * 0.85"
                  :y2="size / 2"
                  :stroke="isYaoCompleted(index + 1) ? yaoColors[index].color : 'rgba(255, 255, 255, 0.1)'"
                />
              </g>
            </svg>
          </div>
        </div>

        <!-- 太极图 -->
        <div class="taiji-container">
          <svg class="taiji-svg animate-rotate" viewBox="0 0 200 200">
            <!-- 外圈 -->
            <circle cx="100" cy="100" r="98" fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="2"/>
            <!-- 白色底 -->
            <circle cx="100" cy="100" r="96" fill="#f5f5f5"/>
            <!-- 黑色阴鱼 - 右半圆 -->
            <path d="M100,4 A96,96 0 0,1 100,196 A48,48 0 0,1 100,100 A48,48 0 0,0 100,4" fill="#1a1a1a"/>
            <!-- 阳鱼眼 - 白色区域中的黑点（上半部） -->
            <circle cx="100" cy="52" r="14" fill="#1a1a1a"/>
            <!-- 阴鱼眼 - 黑色区域中的白点（下半部） -->
            <circle cx="100" cy="148" r="14" fill="#f5f5f5"/>
          </svg>
        </div>
      </div>

      <!-- 状态指示 -->
      <div class="status-indicator">
        <div class="pulse-dot animate-pulse"></div>
        <span class="status-text">{{ progressText }}</span>
      </div>

      <!-- 开始推演/查看报告按钮 -->
      <!-- 推演完成后显示查看报告按钮，其他情况显示开始推演 -->
      <button
        v-if="!dialogueStore.isComplete || outputs.length > 0"
        class="start-divination-btn"
        :disabled="isRunning"
        @click="finalReport ? showReportModal = true : (outputs.length > 0 ? restartDivination() : startDivination())"
      >
        {{ isRunning ? '推演中...' : (finalReport ? '查看最终报告' : (outputs.length > 0 ? '重新开始' : '开始推演')) }}
      </button>
    </section>

    <!-- 右侧推理输出区域 -->
    <section class="output-section">
      <header class="output-header">
        <h2 class="output-title">爻辞解读 - 六爻并行推演，完成后实时展示</h2>
        <div class="output-actions">
          <button class="action-btn" @click="copyOutput">复制</button>
          <button class="action-btn" @click="exportOutput">导出</button>
        </div>
      </header>

      <div class="output-content">
        <!-- 空状态 -->
        <div v-if="outputs.length === 0 && !isRunning" class="empty-state">
          <div class="empty-icon">☯</div>
          <div class="empty-text">点击"开始推演"按钮开始六爻分析</div>
          <div class="empty-subtext">起卦官已完成对话，等待您的确认开始推演</div>
        </div>

        <!-- 推演中状态 -->
        <div v-if="isRunning && outputs.length === 0" class="loading-state">
          <div class="loading-spinner"></div>
          <div class="loading-text">{{ progressText }}</div>
        </div>

        <!-- 推演输出列表 -->
        <div
          v-for="output in outputs"
          :key="output.position"
          class="yao-output animate-fadeIn"
          :class="`yao-${output.position}-active`"
        >
          <div class="yao-output-header">
            <span class="yao-position">第{{ output.position }}爻 · {{ output.lineName }}</span>
            <span v-if="output.yaoCi" class="yao-ci-badge" :title="output.yaoCi">{{ output.yaoCi }}</span>
          </div>
          <div class="yao-interpretation" v-html="renderMarkdown(output.analysis)"></div>
          <div v-if="hasContent(output.advice)" class="yao-advice" v-html="renderMarkdown(output.advice)"></div>
          <div v-if="hasContent(output.risks)" class="yao-risks" v-html="renderMarkdown(output.risks || '')"></div>
        </div>
      </div>
    </section>

    <!-- 最终报告弹窗 -->
    <div v-if="showReportModal" class="modal-overlay" @click="closeReportModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2 class="modal-title">决策参考报告</h2>
          <button class="modal-close" @click="closeReportModal">×</button>
        </div>
        
        <div class="modal-body">
          <div v-if="finalReport" class="report-sections">
            <!-- 六爻摘要 -->
            <div v-if="finalReport.yao_summary && finalReport.yao_summary.length > 0" class="report-section">
              <h3 class="section-title">六爻分析概要</h3>
              <div class="yao-summary-list">
                <div 
                  v-for="yao in finalReport.yao_summary" 
                  :key="yao.position"
                  class="yao-summary-item"
                >
                  <span class="yao-position">{{ yao.line_name }}</span>
                  <span class="yao-brief" v-html="renderMarkdown(yao.brief)"></span>
                </div>
              </div>
            </div>
            
            <div class="report-section">
              <h3 class="section-title">综合建议</h3>
              <div class="section-content" v-html="renderMarkdown(finalReport.overall_advice)"></div>
            </div>
            
            <div v-if="keyRisksList.length > 0" class="report-section">
              <h3 class="section-title">关键风险</h3>
              <ul class="risk-list">
                <li v-for="(risk, index) in keyRisksList" :key="index">
                  {{ risk }}
                </li>
              </ul>
            </div>
            
            <div class="report-section">
              <h3 class="section-title">时机判断</h3>
              <div class="section-content" v-html="renderMarkdown(finalReport.timing_judgment)"></div>
            </div>
            
            <div v-if="finalReport.next_steps && finalReport.next_steps.length > 0" class="report-section">
              <h3 class="section-title">下一步行动</h3>
              <ul class="next-steps">
                <li v-for="(step, index) in finalReport.next_steps" :key="index">
                  {{ index + 1 }}. {{ step }}
                </li>
              </ul>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="modal-btn primary" @click="closeReportModal">知道了</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.divination-view {
  display: flex;
  height: calc(100vh - 73px);
  background-color: var(--bg-color);
}

/* ========== 左侧图形区域 ========== */
.graphics-section {
  width: 45%;
  min-width: 500px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  border-right: 1px solid var(--border-color);
  position: relative;
}

/* 算卦核心区域 */
.divination-stage {
  position: relative;
  width: 500px;
  height: 500px;
}

/* 六爻同心圆容器 */
.yao-rings-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.yao-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.08);
  transition: all 0.5s ease;
}

.yao-ring.active {
  border-width: 3px;
}

/* 爻线 SVG */
.yao-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.yao-line {
  fill: none;
  stroke-width: 3;
  transition: all 0.5s ease;
}

.yao-line.yang,
.yao-line.yin {
  filter: drop-shadow(0 0 8px currentColor);
}

/* 太极图容器 */
.taiji-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
}

.taiji-svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.3));
}

/* 八卦方位 */
.bagua-directions {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.bagua-char {
  position: absolute;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.25);
  letter-spacing: 2px;
  transform: translate(-50%, -50%);
  font-family: var(--font-serif);
}

.bagua-char.qian { top: 3%; left: 50%; }
.bagua-char.kun { top: 97%; left: 50%; }
.bagua-char.zhen { top: 78%; left: 88%; }
.bagua-char.xun { top: 22%; left: 88%; }
.bagua-char.kan { top: 78%; left: 12%; }
.bagua-char.li { top: 22%; left: 12%; }
.bagua-char.gen { top: 50%; left: 95%; }
.bagua-char.dui { top: 50%; left: 5%; }

/* 状态指示 */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 30px;
  padding: 12px 24px;
  background: rgba(155, 89, 182, 0.1);
  border: 1px solid rgba(155, 89, 182, 0.3);
  border-radius: 30px;
  max-width: min(520px, 90%);
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background: var(--accent-purple);
  border-radius: 50%;
}

.status-text {
  font-size: 14px;
  color: var(--accent-purple);
  letter-spacing: 1px;
  font-family: var(--font-serif);
  white-space: normal;
  text-align: center;
}

/* 开始推演按钮 */
.start-divination-btn {
  margin-top: 20px;
  padding: 14px 40px;
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(155, 89, 182, 0.1));
  border: 1px solid var(--yang-color);
  border-radius: 30px;
  color: var(--yang-color);
  font-size: 15px;
  letter-spacing: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-family: var(--font-serif);
}

.start-divination-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(155, 89, 182, 0.2));
  box-shadow: 0 0 30px var(--glow-gold);
}

.start-divination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ========== 右侧推理输出区域 ========== */
.output-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 30px 40px;
  overflow: hidden;
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.output-title {
  font-size: 16px;
  letter-spacing: 2px;
  color: var(--text-secondary);
  font-family: var(--font-serif);
  font-weight: normal;
}

.output-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-family: var(--font-serif);
}

.action-btn:hover {
  border-color: var(--yang-color);
  color: var(--yang-color);
}

.output-content {
  flex: 1;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 24px;
  overflow-y: auto;
}

/* 空状态 */
.empty-state {
  text-align: center;
  color: var(--text-secondary);
  padding: 60px 0;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 15px;
  margin-bottom: 8px;
}

.empty-subtext {
  font-size: 13px;
  opacity: 0.7;
}

/* 加载状态 */
.loading-state {
  text-align: center;
  padding: 60px 0;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 215, 0, 0.2);
  border-top-color: var(--yang-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 14px;
  color: var(--accent-purple);
  letter-spacing: 2px;
  font-family: var(--font-serif);
}

/* 爻输出项 */
.yao-output {
  margin-bottom: 24px;
  padding: 16px;
  padding-left: 20px;
  border-left: 2px solid transparent;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.5s ease;
  animation: fadeIn 0.5s ease;
}

.yao-output:last-child {
  margin-bottom: 0;
}

.yao-output.yao-1-active { border-left-color: var(--yao-1-color); }
.yao-output.yao-2-active { border-left-color: var(--yao-2-color); }
.yao-output.yao-3-active { border-left-color: var(--yao-3-color); }
.yao-output.yao-4-active { border-left-color: var(--yao-4-color); }
.yao-output.yao-5-active { border-left-color: var(--yao-5-color); }
.yao-output.yao-6-active { border-left-color: var(--yao-6-color); }

.yao-output-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  min-width: 0;
}

.yao-position {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 2px;
  flex: 0 0 auto;
}

.yao-output.yao-1-active .yao-position { color: var(--yao-1-color); }
.yao-output.yao-2-active .yao-position { color: var(--yao-2-color); }
.yao-output.yao-3-active .yao-position { color: var(--yao-3-color); }
.yao-output.yao-4-active .yao-position { color: var(--yao-4-color); }
.yao-output.yao-5-active .yao-position { color: var(--yao-5-color); }
.yao-output.yao-6-active .yao-position { color: var(--yao-6-color); }

.yao-ci-badge {
  font-size: 12px;
  padding: 4px 8px;
  background: rgba(255, 215, 0, 0.15);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 4px;
  color: var(--yang-color);
  font-family: var(--font-serif);
  max-width: 55%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 0 1 auto;
}

.yao-interpretation {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 8px;
  font-family: var(--font-serif);
}

.yao-advice {
  font-size: 13px;
  line-height: 1.6;
  color: var(--accent-purple);
  font-family: var(--font-serif);
}

.yao-risks {
  font-size: 13px;
  line-height: 1.6;
  color: var(--accent-red, #e74c3c);
  font-family: var(--font-serif);
  margin-top: 8px;
}

/* Markdown rendered content styles */
.yao-interpretation :deep(p),
.yao-advice :deep(p),
.yao-risks :deep(p) {
  margin: 0 0 8px 0;
}

.yao-interpretation :deep(p:last-child),
.yao-advice :deep(p:last-child),
.yao-risks :deep(p:last-child) {
  margin-bottom: 0;
}

.yao-interpretation :deep(strong),
.yao-advice :deep(strong),
.yao-risks :deep(strong) {
  color: inherit;
  font-weight: 600;
}

.yao-interpretation :deep(ul),
.yao-advice :deep(ul),
.yao-risks :deep(ul) {
  margin: 4px 0;
  padding-left: 20px;
}

.yao-interpretation :deep(li),
.yao-advice :deep(li),
.yao-risks :deep(li) {
  margin: 2px 0;
}

/* 报告弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: #1a1a2e;
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 0 40px rgba(255, 215, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-title {
  font-size: 18px;
  letter-spacing: 4px;
  color: var(--yang-color);
  font-family: var(--font-serif);
  font-weight: 600;
}

.modal-close {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 28px;
  cursor: pointer;
  transition: color 0.3s;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  color: var(--yang-color);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.report-sections {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.report-section {
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.report-section:last-child {
  border-bottom: none;
}

.section-title {
  font-size: 15px;
  letter-spacing: 3px;
  color: var(--yang-color);
  font-family: var(--font-serif);
  margin-bottom: 12px;
}

/* 六爻摘要样式 */
.yao-summary-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.yao-summary-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  border-left: 3px solid var(--yang-color);
}

.yao-position {
  font-size: 13px;
  font-weight: 600;
  color: var(--yang-color);
  font-family: var(--font-serif);
  white-space: nowrap;
  min-width: 40px;
}

.yao-brief {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  font-family: var(--font-serif);
}

.yao-brief :deep(p) {
  margin: 0;
}

.section-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  font-family: var(--font-serif);
}

.section-content :deep(p) {
  margin: 0 0 8px 0;
}

.section-content :deep(p:last-child) {
  margin-bottom: 0;
}

.section-content :deep(strong) {
  color: inherit;
  font-weight: 600;
}

.section-content :deep(ul),
.section-content :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.section-content :deep(li) {
  margin: 4px 0;
}

.next-steps {
  list-style: none;
  padding: 0;
  margin: 0;
}

.next-steps li {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  font-family: var(--font-serif);
  padding-left: 24px;
  position: relative;
  margin-bottom: 8px;
}

.next-steps li::before {
  content: '▸';
  position: absolute;
  left: 0;
  color: var(--yang-color);
}

.risk-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.risk-list li {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  font-family: var(--font-serif);
  padding-left: 24px;
  position: relative;
  margin-bottom: 8px;
}

.risk-list li::before {
  content: '⚠';
  position: absolute;
  left: 0;
  color: #ff6b6b;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-btn {
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 14px;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.3s;
  font-family: var(--font-serif);
  border: 1px solid transparent;
}

.modal-btn.primary {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(155, 89, 182, 0.2));
  border-color: var(--yang-color);
  color: var(--yang-color);
}

.modal-btn.primary:hover {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.3), rgba(155, 89, 182, 0.3));
  box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
}

/* 动画定义 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .divination-view {
    flex-direction: column;
    height: auto;
    min-height: calc(100vh - 73px);
  }

  .graphics-section {
    width: 100%;
    min-width: auto;
    padding: 30px 20px;
    border-right: none;
    border-bottom: 1px solid var(--border-color);
  }

  .divination-stage {
    width: 350px;
    height: 350px;
  }

  .output-section {
    padding: 20px;
    min-height: 400px;
  }
}

@media (max-width: 480px) {
  .divination-stage {
    width: 280px;
    height: 280px;
  }

  .bagua-char {
    font-size: 11px;
  }
}
</style>

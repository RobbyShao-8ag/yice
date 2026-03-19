<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDialogueStore } from '../stores/dialogue'
import { websocketService, type WebSocketMessage } from '../services/websocket'

interface Message {
  id: number
  type: 'officer' | 'user'
  content: string
  time: string
  options?: string[]
}

const router = useRouter()
const dialogueStore = useDialogueStore()

const messages = ref<Message[]>([])
const inputMessage = ref('')
const chatMessagesRef = ref<HTMLElement | null>(null)
const isLoading = ref(false)
const isDialogueComplete = ref(false)
let messageIdCounter = 1

const formatTime = (): string => {
  const now = new Date()
  return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatMessagesRef.value) {
    chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
  }
}

const sendMessage = async (content: string) => {
  if (!content.trim() || isLoading.value) return

  addMessage(content, 'user')
  inputMessage.value = ''
  isLoading.value = true

  try {
    websocketService.sendAgentMessage(content)
  } catch (error) {
    console.error('Failed to send message:', error)
    addMessage('消息发送失败，请检查网络连接。', 'officer')
    isLoading.value = false
  }
}

const isOtherOption = (text: string): boolean => {
  return ['其他', '其他问题', '详细说明', '边走边看', '不太确定', '不确定', '其他情况'].some(
    keyword => text.includes(keyword)
  )
}

const sendQuickReply = (text: string) => {
  // 检测是否是"其他"类宽泛选项
  if (isOtherOption(text)) {
    // 不发送，focus 到输入框让用户自己输入
    inputMessage.value = ''
    // 等待 DOM 渲染后 focus
    nextTick(() => {
      const textarea = document.querySelector('.message-input') as HTMLTextAreaElement
      if (textarea) {
        textarea.focus()
      }
    })
  } else {
    sendMessage(text)
  }
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage(inputMessage.value)
  }
}

const addMessage = (content: string, type: 'officer' | 'user', options?: string[]) => {
  messages.value.push({
    id: messageIdCounter++,
    type,
    content,
    time: formatTime(),
    options
  })
  scrollToBottom()
}

const goToDivination = () => {
  router.push('/divination')
}

const handleAgentMessage = (data: WebSocketMessage) => {
  console.log('Received message:', data)
  
  // Handle dialogue complete
  if (data.type === 'dialogue_complete') {
    isLoading.value = false
    isDialogueComplete.value = true
    dialogueStore.isComplete = true
    // 保存完整的 question_context
    if (data.question_context) {
      dialogueStore.setQuestionContext(data.question_context)
    }
    addMessage('信息收集完成，点击左侧按钮开始推演。', 'officer')
    return
  }
  
  // Handle assistant chunk (streaming text) - 后端发送完整内容，替换最后一条助手消息
  if (data.type === 'assistant_chunk' && data.content) {
    const lastMessage = messages.value[messages.value.length - 1]
    // 如果最后一条是助手消息且正在加载中，替换它
    if (lastMessage && lastMessage.type === 'officer' && isLoading.value && lastMessage.id === messageIdCounter - 1) {
      lastMessage.content = data.content
    } else {
      // 否则添加新消息
      addMessage(data.content, 'officer')
    }
    return
  }
  
  // Handle assistant complete (final message with options)
  // 可能只有 options 没有 content（紧接在 assistant_chunk 之后）
  if (data.type === 'assistant_complete') {
    isLoading.value = false
    
    // 如果有 content，添加新消息
    if (data.content) {
      addMessage(data.content, 'officer', data.options)
    } else if (data.options && data.options.length > 0) {
      // 如果没有 content，给最后一条助手消息添加 options
      const lastMessage = messages.value[messages.value.length - 1]
      if (lastMessage && lastMessage.type === 'officer') {
        lastMessage.options = data.options
      }
    }
    // 如果既没有 content 也没有 options，说明只是表示消息发送完毕（如欢迎消息）
    return
  }
  
  // Handle error
  if (data.type === 'error') {
    isLoading.value = false
    addMessage(`错误：${data.message || '未知错误'}`, 'officer')
    return
  }
}

onMounted(() => {
  websocketService.connect('agent')
  websocketService.onMessage(handleAgentMessage)
  // Add welcome message when component mounts
  addMessage('您好，欢迎使用易策 AI 决策系统。我是您的起卦官，请问您今天想问什么事情？', 'officer')
  scrollToBottom()
})

onUnmounted(() => {
  websocketService.disconnect()
})
</script>

<template>
  <div class="home-view">
    <section class="officer-section">
      <div class="officer-avatar animate-breathe">
        <img src="@/assets/qiguaguan.png" alt="起卦官" class="officer-image"/>
      </div>
      <div class="officer-subtitle">
        六爻推演 · 决策参考<br>
        <span class="officer-subtitle-small">以《周易》智慧，助您明辨前路</span>
      </div>
      <button v-if="isDialogueComplete" class="start-divination-btn" @click="goToDivination">
        开始推演
      </button>
      <div v-else class="dialogue-progress">
        <span class="progress-text">对话收集中...</span>
      </div>
    </section>

    <section class="chat-section">
      <header class="chat-header"><h2>决策咨询</h2></header>

      <div ref="chatMessagesRef" class="chat-messages">
        <div v-for="message in messages" :key="message.id" class="message animate-fadeIn" :class="message.type">
          <div class="message-avatar">{{ message.type === 'officer' ? '☯' : '🙂' }}</div>
          <div class="message-body">
            <div class="message-content">{{ message.content }}</div>
            <div v-if="message.options" class="quick-options">
              <button v-for="option in message.options" :key="option" class="quick-option" :class="{'quick-option-other': isOtherOption(option)}" @click="sendQuickReply(option)">
                {{ option }}
              </button>
            </div>
            <div class="message-time">{{ message.time }}</div>
          </div>
        </div>

        <div v-if="isLoading" class="message officer loading">
          <div class="message-avatar">☯</div>
          <div class="message-body"><div class="typing-indicator"><span></span><span></span><span></span></div></div>
        </div>
      </div>

      <footer class="chat-input-area">
        <div class="input-wrapper">
          <textarea v-model="inputMessage" class="message-input" placeholder="请输入您的回答..." :disabled="isLoading" @keydown="handleKeydown" rows="2"></textarea>
          <button class="send-button" :disabled="!inputMessage.trim() || isLoading" @click="sendMessage(inputMessage)">
            <span v-if="!isLoading">发送</span>
            <span v-else class="loading-spinner"></span>
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.home-view { display: flex; height: calc(100vh - 64px); background: var(--bg-color); }
.officer-section { width: 40%; min-width: 360px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px; border-right: 1px solid var(--border-color); }
.officer-avatar { width: 320px; height: 320px; border-radius: 50%; background: transparent; overflow: hidden; border: 4px solid rgba(255, 215, 0, 0.5); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 80px rgba(255, 215, 0, 0.25); }
.officer-image { width: 100%; height: 100%; object-fit: contain; border-radius: 50%; display: block; }
.officer-subtitle { margin-top: 32px; font-size: 16px; color: var(--text-secondary); letter-spacing: 2px; text-align: center; font-family: var(--font-serif); line-height: 1.8; }
.officer-subtitle-small { font-size: 13px; opacity: 0.7; }
.start-divination-btn { margin-top: 40px; padding: 18px 56px; background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(155, 89, 182, 0.2)); border: 2px solid var(--yang-color); color: var(--text-primary); border-radius: 8px; font-size: 18px; cursor: pointer; transition: all var(--transition-normal); font-family: var(--font-serif); letter-spacing: 1px; }
.start-divination-btn:hover { background: linear-gradient(135deg, rgba(255, 215, 0, 0.3), rgba(155, 89, 182, 0.3)); box-shadow: 0 0 30px rgba(255, 215, 0, 0.3); }
.dialogue-progress { margin-top: 40px; text-align: center; color: var(--text-secondary); font-size: 15px; }
.chat-section { width: 60%; flex: none; display: flex; flex-direction: column; min-width: 0; }
.chat-header { padding: 24px 32px; border-bottom: 1px solid var(--border-color); }
.chat-header h2 { font-size: 20px; font-weight: 500; color: var(--text-primary); font-family: var(--font-serif); }
.chat-messages { flex: 1; overflow-y: auto; padding: 32px; display: flex; flex-direction: column; gap: 24px; }
.message { display: flex; gap: 16px; max-width: 85%; }
.message.officer { align-self: flex-start; }
.message.user { align-self: flex-end; flex-direction: row-reverse; }
.message-avatar { width: 40px; height: 40px; border-radius: 50%; background: rgba(255, 215, 0, 0.1); border: 2px solid rgba(255, 215, 0, 0.3); display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.message.user .message-avatar { background: rgba(155, 89, 182, 0.1); border-color: rgba(155, 89, 182, 0.3); }
.message-body { display: flex; flex-direction: column; gap: 8px; }
.message-content { padding: 16px 20px; border-radius: 12px; line-height: 1.6; font-size: 15px; }
.message.officer .message-content { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: var(--text-primary); }
.message.user .message-content { background: linear-gradient(135deg, rgba(155, 89, 182, 0.2), rgba(155, 89, 182, 0.1)); border: 1px solid rgba(155, 89, 182, 0.3); color: var(--text-primary); }
.quick-options { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.quick-option { padding: 8px 16px; background: rgba(255, 215, 0, 0.1); border: 1px solid rgba(255, 215, 0, 0.3); color: var(--yang-color); border-radius: 20px; font-size: 13px; cursor: pointer; transition: all var(--transition-fast); }
.quick-option:hover { background: rgba(255, 215, 0, 0.2); border-color: var(--yang-color); }
.quick-option-other { background: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.2); color: var(--text-secondary); }
.quick-option-other:hover { background: rgba(255, 255, 255, 0.1); border-color: var(--text-secondary); }
.message-time { font-size: 12px; color: var(--text-secondary); opacity: 0.7; }
.typing-indicator { display: flex; gap: 4px; padding: 16px 20px; }
.typing-indicator span { width: 8px; height: 8px; background: var(--text-secondary); border-radius: 50%; animation: typing 1.4s infinite; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-10px); opacity: 1; } }
.chat-input-area { padding: 24px 32px; border-top: 1px solid var(--border-color); background: rgba(0, 0, 0, 0.3); }
.input-wrapper { display: flex; gap: 12px; max-width: 900px; margin: 0 auto; }
.message-input { flex: 1; padding: 14px 18px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; color: var(--text-primary); font-size: 15px; resize: none; font-family: inherit; transition: all var(--transition-fast); }
.message-input:focus { outline: none; border-color: var(--yang-color); background: rgba(255, 255, 255, 0.08); }
.send-button { padding: 0 32px; background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(155, 89, 182, 0.2)); border: 2px solid rgba(255, 215, 0, 0.5); color: var(--text-primary); border-radius: 12px; font-size: 15px; cursor: pointer; transition: all var(--transition-fast); font-family: var(--font-serif); min-width: 100px; }
.send-button:hover:not(:disabled) { background: linear-gradient(135deg, rgba(255, 215, 0, 0.3), rgba(155, 89, 182, 0.3)); border-color: var(--yang-color); }
.send-button:disabled { opacity: 0.4; cursor: not-allowed; }
.loading-spinner { display: inline-block; width: 18px; height: 18px; border: 2px solid rgba(255, 255, 255, 0.3); border-top-color: var(--yang-color); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 1200px) { .officer-section { width: 360px; min-width: 360px; } .chat-section { width: calc(100% - 360px); } }
@media (max-width: 768px) { .home-view { flex-direction: column; } .officer-section { width: 100%; min-width: 100%; padding: 32px 24px; border-right: none; border-bottom: 1px solid var(--border-color); } .chat-section { width: 100%; } .officer-avatar { width: 240px; height: 240px; } }
</style>

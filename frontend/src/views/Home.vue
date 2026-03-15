<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const healthStatus = ref(null)

const navigateTo = (path) => {
  router.push(path)
}

onMounted(async () => {
  try {
    healthStatus.value = await api.health()
  } catch (e) {
    console.error('健康检查失败:', e)
  }
})
</script>

<template>
  <div class="home-container">
    <!-- 背景图案 (将在CSS中应用用户提供的背景图) -->

    <!-- 顶部标题 -->
    <h1 class="main-title">钢筋工程智能管控平台</h1>

    <!-- 宫格卡片 -->
    <div class="card-grid">
      
      <!-- 卡片1: 隐蔽工程验收 -->
      <div class="card card-white" @click="navigateTo('/hidden-inspection')">
        <div class="icon-circle">
          <svg viewBox="0 0 64 64" width="44" height="44" xmlns="http://www.w3.org/2000/svg">
            <!-- 3D Cube -->
            <path d="M32 34 L54 22 L54 46 L32 58 Z" fill="#005BFF"/>
            <path d="M10 22 L32 34 L32 58 L10 46 Z" fill="#0084FF"/>
            <path d="M32 10 L54 22 L32 34 L10 22 Z" fill="#4B9DFF"/>
            <!-- Stars/Diamonds -->
            <polygon points="20,38 24,40 20,42 16,40" fill="#FFFFFF" opacity="0.9"/>
            <polygon points="24,46 26,47 24,48 22,47" fill="#FFFFFF" opacity="0.9"/>
            <polygon points="44,38 48,40 44,42 40,40" fill="#FFFFFF" opacity="0.5"/>
          </svg>
        </div>
        <div class="card-text">
          <h3>隐蔽工程验收</h3>
          <p>AI 智能识别构件钢筋轮廓，自动测算分布间距并比对设计规格，保障浇筑前隐蔽验收质量。</p>
        </div>
      </div>

      <!-- 卡片2: 进场材料验收 -->
      <div class="card card-blue" @click="navigateTo('/material-inspection')">
        <div class="icon-circle">
          <svg viewBox="0 0 64 64" width="38" height="38" xmlns="http://www.w3.org/2000/svg">
            <rect x="30" y="8" width="22" height="48" rx="2" fill="none" stroke="#246DFF" stroke-width="4"/>
            <rect x="12" y="8" width="24" height="48" rx="4" fill="#246DFF"/>
            <rect x="18" y="20" width="12" height="4" rx="2" fill="#FFD700"/>
            <rect x="18" y="32" width="12" height="4" rx="2" fill="#FFD700"/>
            <rect x="18" y="44" width="12" height="4" rx="2" fill="#FFFFFF"/>
          </svg>
        </div>
        <div class="card-text">
          <h3>进场材料验收</h3>
          <p>现场实拍进场钢筋端面，AI 秒级智能计数与直径估算；支持参照物标定，精确测量钢筋截面尺寸。</p>
        </div>
      </div>

      <!-- 卡片3: 原材微观检测 -->
      <div class="card card-dark" @click="navigateTo('/micro-inspection')">
        <div class="icon-circle">
          <svg viewBox="0 0 64 64" width="38" height="38" xmlns="http://www.w3.org/2000/svg">
             <rect x="16" y="28" width="10" height="24" rx="1" fill="#4BA0FF"/>
             <rect x="28" y="12" width="10" height="40" rx="1" fill="#246DFF"/>
             <rect x="40" y="22" width="10" height="30" rx="1" fill="#0043C8"/>
             <path d="M16 28 L21 23 L26 28 Z" fill="#E6F0FF"/>
             <path d="M28 12 L33 7 L38 12 Z" fill="#E6F0FF"/>
             <path d="M40 22 L45 17 L50 22 Z" fill="#E6F0FF"/>
          </svg>
        </div>
        <div class="card-text">
          <h3>原材微观检测</h3>
          <p>AI 视觉大模型识别钢筋表面轧印标识，自动提取牌号级别、抗震标记（E）及公称直径，无需手工录入。</p>
        </div>
      </div>

      <!-- 卡片4: 检测数据中心 -->
      <div class="card card-dark" @click="navigateTo('/records')">
        <div class="icon-circle">
          <svg viewBox="0 0 64 64" width="44" height="44" xmlns="http://www.w3.org/2000/svg">
            <path d="M32 20 L54 30 L54 54 L32 44 Z" fill="#005BFF"/>
            <path d="M10 30 L32 20 L32 44 L10 54 Z" fill="#0084FF"/>
            <path d="M32 10 L54 20 L32 30 L10 20 Z" fill="#246DFF"/>
            <polygon points="10,20 32,10 26,4 4,14" fill="#6FAEFF"/>
            <polygon points="54,20 32,10 38,4 60,14" fill="#4BA0FF"/>
          </svg>
        </div>
        <div class="card-text">
          <h3>检测数据中心</h3>
          <p>云端汇总所有检测报告与历史记录，支持多维度台账筛选及合规报表一键导出。</p>
        </div>
      </div>

    </div>

    <!-- 底部状态栏 -->
    <div class="status-container" v-if="healthStatus">
       <!-- 底部蓝色科技发光区域 -->
       <div class="glow-bg"></div>
       
       <div class="status-items">
         <!-- 数据库连接 -->
         <div class="status-item">
           <svg viewBox="0 0 16 16" width="14" height="14" xmlns="http://www.w3.org/2000/svg">
              <path d="M8 2 L14 5 L14 11 L8 14 L2 11 L2 5 Z" fill="none" stroke="#4ADE80" stroke-width="1.5"/>
              <circle cx="8" cy="8" r="2.5" fill="#4ADE80"/>
           </svg>
           <span>数据库已连接</span>
         </div>
         <!-- MinIO 连接 -->
         <div class="status-item">
           <svg viewBox="0 0 16 16" width="14" height="14" xmlns="http://www.w3.org/2000/svg">
              <rect x="2" y="3" width="12" height="10" rx="2" fill="none" stroke="#4ADE80" stroke-width="1.5"/>
              <path d="M5 6 h6 M5 10 h3" stroke="#4ADE80" stroke-width="1.5" stroke-linecap="round"/>
           </svg>
           <span>MinIO已连接</span>
         </div>
         <!-- API 服务 -->
         <div class="status-item">
           <svg viewBox="0 0 16 16" width="14" height="14" xmlns="http://www.w3.org/2000/svg">
              <circle cx="8" cy="8" r="7" fill="none" stroke="#4ADE80" stroke-width="1.5"/>
              <path d="M5 8 L7 10 L11 6" stroke="#4ADE80" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
           </svg>
           <span>API服务正常</span>
         </div>
          </div>
       </div>
  </div>
</template>

<style scoped>
/* ========== 液态光泽动画 ========== */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

@keyframes pulseGlow {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.home-container {
  min-height: 100vh;
  position: relative;
  /* 多层渐变背景，增加深度 (如果有背景图，将在此基础上覆盖) */
  background:
    radial-gradient(ellipse at 20% 0%, rgba(100, 160, 255, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(60, 120, 255, 0.06) 0%, transparent 50%),
    linear-gradient(180deg, #E2EDFA 0%, #EDF3FC 30%, #F5F8FF 60%, #FFFFFF 100%);
  background-image: url('../assets/11.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* 主标题 — 渐变文字 + 文字阴影 */
.main-title {
  margin-top: 10vh;
  margin-bottom: 6vh;
  font-size: 46px;
  font-weight: 900;
  background: linear-gradient(135deg, #0A1628 0%, #1A3A7C 50%, #2B5FBF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 4px;
  z-index: 1;
  text-shadow: none;
  filter: drop-shadow(0 2px 4px rgba(10, 22, 40, 0.15));
}

/* 2x2 网格容器 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(2, 480px);
  gap: 40px;
  z-index: 1;
}

/* 响应式：针对小屏幕 */
@media (max-width: 1050px) {
  .card-grid {
    grid-template-columns: 1fr;
    max-width: 480px;
    width: 90%;
  }
}

/* ========== 统一的卡片基础样式 (凹凸+玻璃) ========== */
.card {
  height: 165px;
  border-radius: 24px;
  padding: 0 40px;
  display: flex;
  align-items: center;
  gap: 28px;
  cursor: pointer;
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.35s cubic-bezier(0.4, 0, 0.2, 1),
              border-color 0.3s ease;
  box-sizing: border-box;
  text-decoration: none;
  position: relative;
  overflow: hidden;
}

.card:hover {
  transform: translateY(-6px) scale(1.01);
}

/* 卡片顶部液态光泽条 */
.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.6) 20%,
    rgba(255, 255, 255, 0.9) 50%,
    rgba(255, 255, 255, 0.6) 80%,
    transparent 100%);
  z-index: 2;
}

/* ========== 圆形图标底座 (neumorphism凹凸) ========== */
.icon-circle {
  width: 84px;
  height: 84px;
  border-radius: 50%;
  background: linear-gradient(145deg, #ffffff 0%, #f0f4fa 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  /* 凹凸阴影：外部浮起 + 内部高光 */
  box-shadow:
    6px 6px 16px rgba(0, 40, 100, 0.1),
    -4px -4px 12px rgba(255, 255, 255, 0.9),
    inset 0 2px 4px rgba(255, 255, 255, 0.8),
    inset 0 -2px 6px rgba(0, 30, 80, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.7);
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}

.card:hover .icon-circle {
  box-shadow:
    8px 8px 20px rgba(0, 40, 100, 0.14),
    -5px -5px 15px rgba(255, 255, 255, 0.95),
    inset 0 2px 4px rgba(255, 255, 255, 0.8),
    inset 0 -2px 6px rgba(0, 30, 80, 0.06);
  transform: scale(1.04);
}

/* ========== 卡片主题变体 ========== */

/* 1. 白色磨砂玻璃卡片 (隐蔽工程) */
.card-white {
  background: linear-gradient(135deg,
    rgba(255, 255, 255, 0.85) 0%,
    rgba(240, 248, 255, 0.75) 100%);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow:
    0 8px 32px rgba(30, 90, 200, 0.1),
    0 2px 8px rgba(30, 90, 200, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(0, 40, 100, 0.03);
}
.card-white:hover {
  border-color: rgba(100, 170, 255, 0.3);
  box-shadow:
    0 16px 48px rgba(30, 90, 200, 0.15),
    0 4px 12px rgba(30, 90, 200, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.95),
    inset 0 -1px 0 rgba(0, 40, 100, 0.03);
}
/* 液态光泽扫过效果 */
.card-white::after {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0; right: 0;
  background: linear-gradient(105deg,
    transparent 30%,
    rgba(255, 255, 255, 0.4) 45%,
    rgba(255, 255, 255, 0.6) 50%,
    rgba(255, 255, 255, 0.4) 55%,
    transparent 70%);
  background-size: 200% 100%;
  animation: shimmer 6s ease-in-out infinite;
  border-radius: 22px;
  pointer-events: none;
  z-index: 1;
}
.card-white h3 {
  color: #0E1A35;
  font-size: 24px;
  margin: 0 0 10px;
  font-weight: 800;
}
.card-white p {
  color: #8A96AC;
  font-size: 13px;
  margin: 0;
  line-height: 1.5;
}

/* 2. 亮蓝玻璃渐变卡片 (进场材料) */
.card-blue {
  background: linear-gradient(135deg,
    rgba(79, 163, 255, 0.92) 0%,
    rgba(41, 116, 255, 0.95) 100%);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid rgba(120, 190, 255, 0.4);
  box-shadow:
    0 8px 32px rgba(41, 116, 255, 0.3),
    0 2px 8px rgba(41, 116, 255, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.25),
    inset 0 -1px 0 rgba(0, 20, 80, 0.15);
}
.card-blue:hover {
  border-color: rgba(150, 210, 255, 0.5);
  box-shadow:
    0 16px 48px rgba(41, 116, 255, 0.4),
    0 4px 12px rgba(41, 116, 255, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    inset 0 -1px 0 rgba(0, 20, 80, 0.15);
}
/* 蓝色卡片上的磨砂光泽 */
.card-blue::after {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0; right: 0;
  background: linear-gradient(105deg,
    transparent 30%,
    rgba(255, 255, 255, 0.15) 45%,
    rgba(255, 255, 255, 0.25) 50%,
    rgba(255, 255, 255, 0.15) 55%,
    transparent 70%);
  background-size: 200% 100%;
  animation: shimmer 7s ease-in-out infinite;
  animation-delay: 1s;
  border-radius: 22px;
  pointer-events: none;
  z-index: 1;
}
.card-blue .icon-circle {
  background: linear-gradient(145deg, #ffffff 0%, #e8f0ff 100%);
  box-shadow:
    4px 4px 12px rgba(0, 30, 100, 0.2),
    -3px -3px 10px rgba(255, 255, 255, 0.5),
    inset 0 2px 4px rgba(255, 255, 255, 0.9),
    inset 0 -2px 4px rgba(0, 30, 80, 0.05);
}
.card-blue h3 {
  color: #ffffff;
  font-size: 24px;
  margin: 0 0 10px;
  font-weight: 800;
  text-shadow: 0 1px 3px rgba(0, 40, 120, 0.3);
}
.card-blue p {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  margin: 0;
  line-height: 1.5;
}

/* 3. 深蓝玻璃渐变卡片 (原材微观、数据中心) */
.card-dark {
  background: linear-gradient(135deg,
    rgba(27, 62, 140, 0.92) 0%,
    rgba(15, 32, 92, 0.95) 100%);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid rgba(80, 130, 220, 0.25);
  box-shadow:
    0 8px 32px rgba(15, 32, 92, 0.4),
    0 2px 8px rgba(15, 32, 92, 0.2),
    inset 0 1px 0 rgba(100, 160, 255, 0.15),
    inset 0 -1px 0 rgba(0, 10, 40, 0.3);
}
.card-dark:hover {
  border-color: rgba(100, 160, 255, 0.35);
  box-shadow:
    0 16px 48px rgba(15, 32, 92, 0.5),
    0 4px 12px rgba(15, 32, 92, 0.25),
    inset 0 1px 0 rgba(100, 160, 255, 0.2),
    inset 0 -1px 0 rgba(0, 10, 40, 0.3);
}
/* 深蓝卡片的微光扫过 */
.card-dark::after {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0; right: 0;
  background: linear-gradient(105deg,
    transparent 30%,
    rgba(100, 170, 255, 0.08) 45%,
    rgba(120, 190, 255, 0.15) 50%,
    rgba(100, 170, 255, 0.08) 55%,
    transparent 70%);
  background-size: 200% 100%;
  animation: shimmer 8s ease-in-out infinite;
  animation-delay: 2s;
  border-radius: 22px;
  pointer-events: none;
  z-index: 1;
}
.card-dark .icon-circle {
  background: linear-gradient(145deg, #ffffff 0%, #e0eaff 100%);
  box-shadow:
    4px 4px 12px rgba(0, 10, 50, 0.3),
    -3px -3px 10px rgba(60, 120, 200, 0.15),
    inset 0 2px 4px rgba(255, 255, 255, 0.9),
    inset 0 -2px 4px rgba(0, 20, 60, 0.08);
}
.card-dark h3 {
  color: #ffffff;
  font-size: 24px;
  margin: 0 0 10px;
  font-weight: 800;
  text-shadow: 0 1px 4px rgba(0, 10, 40, 0.4);
}
.card-dark p {
  color: rgba(200, 215, 240, 0.75);
  font-size: 13px;
  margin: 0;
  line-height: 1.5;
}

/* ========== 底部状态栏 (磨砂玻璃) ========== */

.status-container {
  margin-top: auto;
  margin-bottom: 30px;
  padding-bottom: 20px;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
  width: 100%;
}

/* 文字块 — 磨砂玻璃背景 */
.status-items {
  display: flex;
  gap: 40px;
  z-index: 2;
  margin-bottom: 16px;
  background: rgba(10, 25, 60, 0.45);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  padding: 14px 40px;
  border-radius: 40px;
  border: 1px solid rgba(80, 140, 255, 0.15);
  box-shadow:
    0 4px 20px rgba(0, 20, 80, 0.2),
    inset 0 1px 0 rgba(100, 170, 255, 0.1),
    inset 0 -1px 0 rgba(0, 10, 40, 0.2);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(210, 230, 255, 0.9);
  font-size: 14px;
  font-weight: 500;
}

/* 绿色指示灯发光效果 */
.status-item svg {
  filter: drop-shadow(0 0 4px rgba(74, 222, 128, 0.5));
}

/* 底部科技蓝泛光晕影背景 */
.glow-bg {
  position: absolute;
  top: -100px;
  left: 50%;
  transform: translateX(-50%);
  width: 100vw;
  height: 240px;
  background:
    radial-gradient(ellipse at 50% 100%, rgba(0, 140, 255, 0.12) 0%, transparent 50%),
    radial-gradient(ellipse at 30% 80%, rgba(0, 200, 255, 0.06) 0%, transparent 40%),
    radial-gradient(ellipse at 70% 80%, rgba(0, 200, 255, 0.06) 0%, transparent 40%);
  pointer-events: none;
  z-index: 1;
}
</style>

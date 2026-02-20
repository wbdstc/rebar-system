<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const healthStatus = ref(null)

const menuItems = [
  {
    title: '隐蔽工程验收',
    subtitle: 'Hidden Works Inspection',
    icon: 'Grid',
    color: '#409EFF',
    path: '/workbench?mode=stirrup',
    desc: '箍筋间距 · 板墙间距 · 柱纵筋合规检测'
  },
  {
    title: '进场材料验收',
    subtitle: 'Incoming Material',
    icon: 'Aim',
    color: '#67C23A',
    path: '/workbench?mode=material',
    desc: '钢筋端面计数与直径测量'
  },
  {
    title: '检测数据中心',
    subtitle: 'Data Center',
    icon: 'Document',
    color: '#909399',
    path: '/records',
    desc: '查看与导出历史检测记录'
  }
]

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
    <!-- 顶部标题 -->
    <div class="header">
      <div class="logo">
        <el-icon :size="48" color="#409EFF"><Monitor /></el-icon>
      </div>
      <div class="title-area">
        <h1>钢筋工程智能管控平台</h1>
        <p>Intelligent Rebar Engineering Control System</p>
      </div>
      <div class="version-badge">
        <el-tag type="warning" effect="dark">V13.0 Enterprise</el-tag>
      </div>
    </div>

    <!-- 功能卡片 -->
    <div class="card-grid">
      <div
        v-for="item in menuItems"
        :key="item.path"
        class="feature-card"
        :style="{ '--card-color': item.color }"
        @click="navigateTo(item.path)"
      >
        <div class="card-icon">
          <el-icon :size="64"><component :is="item.icon" /></el-icon>
        </div>
        <div class="card-content">
          <h3>{{ item.title }}</h3>
          <span class="subtitle">{{ item.subtitle }}</span>
          <p>{{ item.desc }}</p>
        </div>
        <div class="card-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 系统状态 -->
    <div class="status-bar" v-if="healthStatus">
      <div class="status-item">
        <el-icon :color="healthStatus.database === 'connected' ? '#67C23A' : '#F56C6C'">
          <component :is="healthStatus.database === 'connected' ? 'CircleCheck' : 'CircleClose'" />
        </el-icon>
        <span>数据库 {{ healthStatus.database === 'connected' ? '已连接' : '未连接' }}</span>
      </div>
      <div class="status-item">
        <el-icon :color="healthStatus.minio === 'connected' ? '#67C23A' : '#F56C6C'">
          <component :is="healthStatus.minio === 'connected' ? 'CircleCheck' : 'CircleClose'" />
        </el-icon>
        <span>MinIO {{ healthStatus.minio === 'connected' ? '已连接' : '未连接' }}</span>
      </div>
      <div class="status-item">
        <el-icon color="#67C23A"><CircleCheck /></el-icon>
        <span>API 服务正常</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1c2c 0%, #2d3748 100%);
  padding: 40px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-bottom: 60px;
  padding: 30px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  backdrop-filter: blur(10px);
}

.title-area {
  text-align: center;
}

.title-area h1 {
  color: #fff;
  font-size: 32px;
  font-weight: 700;
  margin: 0;
  letter-spacing: 2px;
}

.title-area p {
  color: #8b9bb4;
  margin: 8px 0 0;
  font-size: 14px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.feature-card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 32px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  gap: 20px;
}

.feature-card:hover {
  transform: translateY(-8px);
  background: rgba(255, 255, 255, 0.12);
  border-color: var(--card-color);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.card-icon {
  color: var(--card-color);
  flex-shrink: 0;
}

.card-content {
  flex: 1;
}

.card-content h3 {
  color: #fff;
  font-size: 20px;
  margin: 0 0 4px;
}

.card-content .subtitle {
  color: var(--card-color);
  font-size: 12px;
  font-weight: 500;
}

.card-content p {
  color: #8b9bb4;
  font-size: 13px;
  margin: 8px 0 0;
}

.card-arrow {
  color: #8b9bb4;
  transition: transform 0.3s;
}

.feature-card:hover .card-arrow {
  transform: translateX(8px);
  color: var(--card-color);
}

.status-bar {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-top: 60px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #8b9bb4;
  font-size: 14px;
}
</style>

<script setup>
import { ref, reactive, onMounted, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const route = useRoute()
const router = useRouter()

// === 状态定义 ===
const mode = ref('spacing')
const isLoading = ref(false)
const imageFile = ref(null)
const imagePreview = ref(null)
const canvasRef = ref(null)
const imgObj = ref(null)

// 检测参数
const params = reactive({
  confidence: 40,
  overlap: 40,
  refLength: 85.6  // 参照物实际长度 mm
})

// 构件类型 & 间距参数（间距模式专用）
const componentType = ref('slab_wall')  // slab_wall | beam_column
const spacingParams = reactive({
  designSpacing: 150,    // 板/墙设计间距 (mm)
  denseSpacing: 100,     // 梁/柱加密区间距 (mm)
  sparseSpacing: 200,    // 梁/柱非加密区间距 (mm)
  tolerance: 20          // 误差阈值 (mm)
})
const spacingResults = ref([])  // 后端返回的间距检查结果

// 检测结果
const result = reactive({
  predictions: [],
  detected_count: 0,
  image_url: null
})

// 参照物标定状态
const calibration = reactive({
  isDrawing: false,
  startX: 0,
  startY: 0,
  refBox: null,
  pixelPerMm: 0
})

// 模式配置
const modeConfig = {
  spacing: {
    title: '隐蔽验收 - 间距检测',
    subtitle: '检测钢筋网格间距',
    color: '#409EFF'
  },
  counting: {
    title: '进场验收 - 计数检测',
    subtitle: '检测钢筋数量与直径',
    color: '#67C23A'
  }
}

// 计算属性
const currentConfig = computed(() => modeConfig[mode.value] || modeConfig.spacing)

const avgDiameter = computed(() => {
  if (!result.predictions.length || !calibration.pixelPerMm) return '-'
  const diameters = result.predictions.map(p => {
    const minDim = Math.min(p.width, p.height)
    return minDim / calibration.pixelPerMm
  })
  const avg = diameters.reduce((a, b) => a + b, 0) / diameters.length
  return avg.toFixed(1)
})

// 监听路由参数
watch(() => route.query.mode, (newMode) => {
  if (newMode && ['spacing', 'counting'].includes(newMode)) {
    mode.value = newMode
  }
}, { immediate: true })

// === 方法定义 ===

// 处理文件选择
const handleFileChange = (file) => {
  const rawFile = file.raw || file
  imageFile.value = rawFile
  
  // 预览
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target.result
    
    // 加载图片到 canvas
    imgObj.value = new Image()
    imgObj.value.onload = () => {
      resetState()
      nextTick(() => redrawCanvas())
    }
    imgObj.value.src = e.target.result
  }
  reader.readAsDataURL(rawFile)
}

// 重置状态
const resetState = () => {
  result.predictions = []
  result.detected_count = 0
  calibration.refBox = null
  calibration.pixelPerMm = 0
  spacingResults.value = []
}

// 开始检测
const startAnalysis = async () => {
  if (!imageFile.value) {
    ElMessage.warning('请先上传图片')
    return
  }
  
  isLoading.value = true
  spacingResults.value = []
  
  try {
    const formData = new FormData()
    formData.append('image', imageFile.value)
    
    // 构建间距检测扩展参数
    const extraParams = {}
    if (mode.value === 'spacing' && calibration.pixelPerMm > 0) {
      extraParams.component_type = componentType.value
      extraParams.pixel_per_mm = calibration.pixelPerMm
      extraParams.tolerance = spacingParams.tolerance
      if (componentType.value === 'slab_wall') {
        extraParams.target_spacing = spacingParams.designSpacing
      } else {
        extraParams.target_spacing_dense = spacingParams.denseSpacing
        extraParams.target_spacing_sparse = spacingParams.sparseSpacing
      }
    }
    
    const data = await api.analyze(formData, mode.value, params.confidence, params.overlap, extraParams)
    
    result.predictions = data.predictions || []
    result.detected_count = result.predictions.length
    result.image_url = data.image_url
    
    // 存储间距检查结果
    if (data.spacings) {
      spacingResults.value = data.spacings
      const passed = data.spacings.filter(s => s.status !== 'fail').length
      ElMessage.success(`检测完成 | 间距 ${data.spacings.length} 段，合格 ${passed} 段`)
    } else {
      ElMessage.success(`检测完成，识别到 ${result.detected_count} 个目标`)
    }
    
    nextTick(() => redrawCanvas())
    
  } catch (error) {
    ElMessage.error('检测失败: ' + error.message)
  } finally {
    isLoading.value = false
  }
}

// Canvas 绑定鼠标事件
const handleMouseDown = (e) => {
  if (!imgObj.value) return
  
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const mx = (e.clientX - rect.left) * scaleX
  const my = (e.clientY - rect.top) * scaleY
  
  calibration.isDrawing = true
  calibration.startX = mx
  calibration.startY = my
  calibration.refBox = { x: mx, y: my, w: 0, h: 0 }
}

const handleMouseMove = (e) => {
  if (!calibration.isDrawing) return
  
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const mx = (e.clientX - rect.left) * scaleX
  const my = (e.clientY - rect.top) * scaleY
  
  calibration.refBox.w = mx - calibration.startX
  calibration.refBox.h = my - calibration.startY
  
  redrawCanvas()
}

const handleMouseUp = () => {
  if (calibration.isDrawing && calibration.refBox) {
    calibration.isDrawing = false
    
    if (Math.abs(calibration.refBox.w) > 5) {
      const pxW = Math.abs(calibration.refBox.w)
      calibration.pixelPerMm = pxW / params.refLength
      ElMessage.success(`标定完成: ${calibration.pixelPerMm.toFixed(3)} 像素/mm`)
    }
    
    redrawCanvas()
  }
}

// 重绘 Canvas
const redrawCanvas = () => {
  const canvas = canvasRef.value
  if (!canvas || !imgObj.value) return
  
  const ctx = canvas.getContext('2d')
  
  // 设置画布尺寸
  canvas.width = imgObj.value.width
  canvas.height = imgObj.value.height
  
  // 绘制图片
  ctx.drawImage(imgObj.value, 0, 0)
  
  // 绘制参照物框
  if (calibration.refBox && calibration.refBox.w !== 0) {
    ctx.strokeStyle = '#ff9800'
    ctx.lineWidth = 3
    ctx.setLineDash([5, 5])
    ctx.strokeRect(
      calibration.refBox.x, 
      calibration.refBox.y, 
      calibration.refBox.w, 
      calibration.refBox.h
    )
    ctx.setLineDash([])
    ctx.fillStyle = '#ff9800'
    ctx.font = '14px Arial'
    ctx.fillText('参照物', calibration.refBox.x, calibration.refBox.y - 5)
  }
  
  // 绘制检测框
  ctx.strokeStyle = '#00e676'
  ctx.lineWidth = 2
  
  result.predictions.forEach((p, i) => {
    const x = p.x - p.width / 2
    const y = p.y - p.height / 2
    
    ctx.strokeRect(x, y, p.width, p.height)
    
    // 编号
    ctx.fillStyle = '#00e676'
    ctx.font = 'bold 12px Arial'
    ctx.fillText((i + 1).toString(), p.x - 4, p.y + 4)
    
    // 直径（如果已标定）
    if (calibration.pixelPerMm > 0) {
      const dia = (Math.min(p.width, p.height) / calibration.pixelPerMm).toFixed(1)
      ctx.fillStyle = '#fff'
      ctx.font = '10px Arial'
      ctx.fillText(`φ${dia}`, x, y - 3)
    }
  })
  
  // === 绘制间距合规性线条 ===
  if (spacingResults.value.length > 0) {
    spacingResults.value.forEach(sp => {
      const sx = sp.start.x, sy = sp.start.y
      const ex = sp.end.x,   ey = sp.end.y
      const mx = (sx + ex) / 2, my = (sy + ey) / 2
      
      // 画连接线
      ctx.beginPath()
      ctx.strokeStyle = sp.color
      ctx.lineWidth = 3
      ctx.setLineDash([])
      ctx.moveTo(sx, sy)
      ctx.lineTo(ex, ey)
      ctx.stroke()
      
      // 距离标注背景
      const label = `${sp.mm_distance}mm`
      ctx.font = 'bold 13px Arial'
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = 'rgba(0,0,0,0.75)'
      ctx.fillRect(mx - textWidth / 2 - 4, my - 18, textWidth + 8, 20)
      
      // 距离数值
      ctx.fillStyle = sp.color
      ctx.textAlign = 'center'
      ctx.fillText(label, mx, my - 3)
      
      // 状态小标签（显示在数值下方）
      ctx.font = '10px Arial'
      ctx.fillStyle = sp.color
      ctx.fillText(sp.label, mx, my + 12)
      
      ctx.textAlign = 'start'  // 重置
    })
  }
}

// 保存记录
const saveRecord = async () => {
  if (!result.predictions.length) {
    ElMessage.warning('请先进行检测')
    return
  }
  
  try {
    await api.createRecord({
      inspection_type: mode.value,
      detected_count: result.detected_count,
      predictions: result.predictions,
      image_url: result.image_url
    })
    ElMessage.success('记录已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

onMounted(() => {
  if (route.query.mode) {
    mode.value = route.query.mode
  }
})
</script>

<template>
  <el-container class="inspection-container">
    <!-- 侧边栏 -->
    <el-aside width="320px" class="sidebar">
      <!-- 模式切换 -->
      <el-card class="control-card">
        <template #header>
          <div class="card-header">
            <el-icon><Switch /></el-icon>
            <span>检测模式</span>
          </div>
        </template>
        <el-radio-group v-model="mode" class="mode-radio">
          <el-radio-button value="spacing">
            <el-icon><Grid /></el-icon> 间距检测
          </el-radio-button>
          <el-radio-button value="counting">
            <el-icon><Aim /></el-icon> 计数检测
          </el-radio-button>
        </el-radio-group>
      </el-card>

      <!-- 图片上传 -->
      <el-card class="control-card">
        <template #header>
          <div class="card-header">
            <el-icon><Upload /></el-icon>
            <span>图片上传</span>
          </div>
        </template>
        <el-upload
          drag
          :auto-upload="false"
          :show-file-list="false"
          accept="image/*"
          @change="handleFileChange"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽或 <em>点击上传</em></div>
        </el-upload>
      </el-card>

      <!-- 构件类型选择（仅间距模式） -->
      <el-card v-if="mode === 'spacing'" class="control-card">
        <template #header>
          <div class="card-header">
            <el-icon><Grid /></el-icon>
            <span>构件类型</span>
          </div>
        </template>
        <el-radio-group v-model="componentType" class="mode-radio">
          <el-radio-button value="slab_wall">板/墙</el-radio-button>
          <el-radio-button value="beam_column">梁/柱</el-radio-button>
        </el-radio-group>

        <!-- 板/墙：单一间距 -->
        <div v-if="componentType === 'slab_wall'" class="spacing-inputs">
          <div class="param-item">
            <span>设计间距 (mm)</span>
            <el-input-number v-model="spacingParams.designSpacing" :min="10" :max="500" :step="10" />
          </div>
        </div>

        <!-- 梁/柱：双间距 -->
        <div v-else class="spacing-inputs">
          <div class="param-item">
            <span>加密区间距 (mm)</span>
            <el-input-number v-model="spacingParams.denseSpacing" :min="10" :max="500" :step="10" />
          </div>
          <div class="param-item">
            <span>非加密区间距 (mm)</span>
            <el-input-number v-model="spacingParams.sparseSpacing" :min="10" :max="500" :step="10" />
          </div>
        </div>

        <div class="param-item">
          <span>误差阈值 (mm)</span>
          <el-input-number v-model="spacingParams.tolerance" :min="1" :max="50" :step="5" />
        </div>
      </el-card>

      <!-- 参数设置 -->
      <el-card class="control-card">
        <template #header>
          <div class="card-header">
            <el-icon><Setting /></el-icon>
            <span>检测参数</span>
          </div>
        </template>
        <div class="param-item">
          <span>置信度阈值</span>
          <el-slider v-model="params.confidence" :min="10" :max="90" />
        </div>
        <div class="param-item">
          <span>参照物宽度 (mm)</span>
          <el-input-number v-model="params.refLength" :min="1" :max="500" />
        </div>
      </el-card>

      <!-- 开始检测 -->
      <el-button
        type="primary"
        size="large"
        :loading="isLoading"
        :disabled="!imageFile"
        class="analyze-btn"
        @click="startAnalysis"
      >
        <el-icon><Lightning /></el-icon>
        开始智能检测
      </el-button>

      <!-- 检测结果 -->
      <el-card v-if="result.detected_count" class="result-card">
        <template #header>
          <div class="card-header">
            <el-icon><DataAnalysis /></el-icon>
            <span>检测结果</span>
          </div>
        </template>
        <div class="result-stats">
          <div class="stat-item">
            <div class="stat-value">{{ result.detected_count }}</div>
            <div class="stat-label">检测数量</div>
          </div>
          <div class="stat-item" v-if="mode === 'counting'">
            <div class="stat-value">{{ avgDiameter }}</div>
            <div class="stat-label">平均直径 (mm)</div>
          </div>
        </div>

        <!-- 间距检查统计 -->
        <div v-if="spacingResults.length" class="spacing-stats">
          <div class="spacing-stat-row">
            <span class="spacing-stat-label">间距段数</span>
            <span class="spacing-stat-value">{{ spacingResults.length }}</span>
          </div>
          <div class="spacing-stat-row">
            <span class="spacing-stat-label" style="color:#00e676">✓ 合格</span>
            <span class="spacing-stat-value" style="color:#00e676">{{ spacingResults.filter(s => s.status !== 'fail').length }}</span>
          </div>
          <div class="spacing-stat-row">
            <span class="spacing-stat-label" style="color:#ff1744">✗ 不合格</span>
            <span class="spacing-stat-value" style="color:#ff1744">{{ spacingResults.filter(s => s.status === 'fail').length }}</span>
          </div>
        </div>

        <el-button type="success" @click="saveRecord" class="save-btn">
          <el-icon><Document /></el-icon> 保存记录
        </el-button>
      </el-card>
    </el-aside>

    <!-- 主内容区 - Canvas -->
    <el-main class="main-content">
      <div class="canvas-header">
        <h2 :style="{ color: currentConfig.color }">{{ currentConfig.title }}</h2>
        <el-button text @click="router.push('/')">
          <el-icon><Back /></el-icon> 返回首页
        </el-button>
      </div>
      
      <div class="canvas-wrapper">
        <canvas
          ref="canvasRef"
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove"
          @mouseup="handleMouseUp"
          @mouseleave="handleMouseUp"
        ></canvas>
        
        <div v-if="!imagePreview" class="canvas-placeholder">
          <el-icon :size="64"><Picture /></el-icon>
          <p>请上传图片开始检测</p>
        </div>

        <!-- 图例 -->
        <div class="legend-box" v-if="result.predictions.length">
          <div class="legend-item">
            <span class="dot" style="background: #00e676;"></span>
            {{ spacingResults.length ? (componentType === 'beam_column' ? '非加密区合格' : '合格') : '检测框' }}
          </div>
          <div class="legend-item" v-if="spacingResults.length && componentType === 'beam_column'">
            <span class="dot" style="background: #00e5ff;"></span>
            加密区合格
          </div>
          <div class="legend-item" v-if="spacingResults.length">
            <span class="dot" style="background: #ff1744;"></span>
            不合格
          </div>
          <div class="legend-item">
            <span class="dot" style="background: #ff9800;"></span>
            参照物
          </div>
        </div>
      </div>
    </el-main>
  </el-container>
</template>

<style scoped>
.inspection-container {
  height: 100vh;
  background: #1a1c2c;
}

.sidebar {
  background: #2d3748;
  padding: 20px;
  overflow-y: auto;
}

.control-card {
  margin-bottom: 16px;
  background: #3a4556;
  border: none;
}

.control-card :deep(.el-card__header) {
  padding: 12px 16px;
  background: #2d3748;
  border-bottom: 1px solid #4a5568;
}

.control-card :deep(.el-card__body) {
  padding: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e2e8f0;
  font-weight: 600;
}

.mode-radio {
  width: 100%;
}

.mode-radio :deep(.el-radio-button__inner) {
  width: 100%;
}

.param-item {
  margin-bottom: 16px;
}

.param-item span {
  display: block;
  color: #a0aec0;
  font-size: 13px;
  margin-bottom: 8px;
}

.analyze-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  margin-bottom: 16px;
}

.result-card {
  background: linear-gradient(135deg, #1a4731 0%, #22543d 100%);
  border: 1px solid #38a169;
}

.result-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #68d391;
}

.stat-label {
  font-size: 12px;
  color: #9ae6b4;
}

.spacing-inputs {
  margin-top: 12px;
}

.spacing-stats {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.spacing-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
  color: #e2e8f0;
}

.spacing-stat-label {
  font-weight: 500;
}

.spacing-stat-value {
  font-weight: 700;
  font-size: 15px;
}

.save-btn {
  width: 100%;
  margin-top: 12px;
}

.main-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.canvas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.canvas-header h2 {
  margin: 0;
}

.canvas-wrapper {
  flex: 1;
  position: relative;
  background: #111;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.canvas-wrapper canvas {
  max-width: 100%;
  max-height: 100%;
  cursor: crosshair;
}

.canvas-placeholder {
  color: #4a5568;
  text-align: center;
}

.canvas-placeholder p {
  margin-top: 16px;
  font-size: 14px;
}

.legend-box {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(0, 0, 0, 0.8);
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #4a5568;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e2e8f0;
  font-size: 12px;
  margin-bottom: 6px;
}

.legend-item:last-child {
  margin-bottom: 0;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
</style>

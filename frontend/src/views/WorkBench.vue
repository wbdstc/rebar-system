<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const route = useRoute()
const router = useRouter()

// =============================================
// 构件检测模式定义
// =============================================
const inspectionModes = [
  {
    value: 'column_longitudinal',
    label: '柱 - 纵筋检测 (KZ)',
    icon: 'Aim',
    color: '#67C23A',
    backendMode: 'counting',
    desc: '检测柱纵向钢筋数量，比对角筋+中部筋设计值'
  },
  {
    value: 'beam_longitudinal',
    label: '梁 - 主筋检测 (KL)',
    icon: 'Aim',
    color: '#00BCD4',
    backendMode: 'counting',
    desc: '检测梁上下部纵筋数量，比对设计值'
  },
  {
    value: 'stirrup',
    label: '柱/梁 - 箍筋检测 (KZ/KL)',
    icon: 'Grid',
    color: '#409EFF',
    backendMode: 'spacing',
    desc: '检测箍筋间距，区分加密区与非加密区'
  },
  {
    value: 'slab_wall',
    label: '板/墙 - 钢筋检测 (B/Q)',
    icon: 'Grid',
    color: '#E6A23C',
    backendMode: 'spacing',
    desc: '检测板/墙分布钢筋间距，比对设计间距'
  },
  {
    value: 'material',
    label: '进场原材检测 (Material)',
    icon: 'Box',
    color: '#F56C6C',
    backendMode: 'counting',
    desc: '进场钢筋端面计数与直径测量'
  },
  {
    value: 'material_vlm',
    label: '原材微观核验 (VLM)',
    icon: 'View',
    color: '#9C27B0',
    backendMode: 'vlm',
    desc: 'AI 识别钢筋表面轧印，提取牌号/抗震/直径'
  }
]

// =============================================
// 状态定义
// =============================================
const currentMode = ref('stirrup')
const isLoading = ref(false)
const imageFile = ref(null)
const imagePreview = ref(null)
const canvasRef = ref(null)
const imgObj = ref(null)

// 统一平法参数模型
const pingfaParams = reactive({
  column: { corner: 4, middle: 0 },
  beam: { top: 0, bottom: 0, waist: 0 },
  stirrup: { dense: 100, normal: 200 },
  slab: { spacingX: 150, spacingY: 150 }
})

// 进场原材参数
const materialParams = reactive({
  refLength: 85.6
})

// 通用检测参数
const detectParams = reactive({
  confidence: 40,
  overlap: 40,
  tolerance: 20
})

// 标定状态
const calibration = reactive({
  isDrawing: false,
  startX: 0,
  startY: 0,
  refBox: null,
  pixelPerMm: 0
})

// 检测结果
const result = reactive({
  predictions: [],
  detected_count: 0,
  image_url: null
})

// 间距检测结果
const spacingResults = ref([])

// 纵筋合规判定
const complianceResult = reactive({
  status: null,
  message: ''
})

// =============================================
// 原材微观核验状态 (material_vlm)
// =============================================
const materialVerifying = ref(false)
const materialResult = reactive({
  success: false,
  material_grade: '',
  is_seismic: false,
  diameter: 0,
  raw_text: ''
})

// =============================================
// CAD 图纸解析状态（Step 1 · 全局）
// =============================================
const cadFile = ref(null)
const cadPreview = ref(null)
const cadParsing = ref(false)
const cadParseHint = ref('')
const cadParseResult = reactive({
  success: false,
  component_type: '',
  // 柱
  corner_bars: 0,
  middle_bars: 0,
  total_bars: 0,
  stirrup_dense: 0,
  stirrup_normal: 0,
  // 梁
  top_bars_total: 0,
  bottom_bars_total: 0,
  stirrup_legs: 0,
  // 板/墙
  design_spacing: 0
})

// =============================================
// 计算属性
// =============================================
const currentModeConfig = computed(() =>
  inspectionModes.find(m => m.value === currentMode.value) || inspectionModes[0]
)

const backendMode = computed(() => currentModeConfig.value.backendMode)

const designTotal = computed(() => {
  if (currentMode.value === 'column_longitudinal') {
    return pingfaParams.column.corner + pingfaParams.column.middle
  } else if (currentMode.value === 'beam_longitudinal') {
    return pingfaParams.beam.top + pingfaParams.beam.bottom + pingfaParams.beam.waist
  }
  return 0
})

const needsCalibration = computed(() =>
  ['stirrup', 'slab_wall', 'material'].includes(currentMode.value)
)

const avgDiameter = computed(() => {
  if (!result.predictions.length || !calibration.pixelPerMm) return '-'
  const diameters = result.predictions.map(p =>
    Math.min(p.width, p.height) / calibration.pixelPerMm
  )
  return (diameters.reduce((a, b) => a + b, 0) / diameters.length).toFixed(1)
})

// =============================================
// 路由参数处理
// =============================================
onMounted(() => {
  if (route.query.mode && inspectionModes.some(m => m.value === route.query.mode)) {
    currentMode.value = route.query.mode
  }
})

// 切换模式时重置
watch(currentMode, () => {
  resetAll()
})

// =============================================
// 方法
// =============================================
const resetAll = () => {
  result.predictions = []
  result.detected_count = 0
  result.image_url = null
  spacingResults.value = []
  complianceResult.status = null
  complianceResult.message = ''
  calibration.refBox = null
  calibration.pixelPerMm = 0
  calibration.isDrawing = false
  imageFile.value = null
  imagePreview.value = null
  imgObj.value = null

  // 重置原材核验状态
  materialVerifying.value = false
  materialResult.success = false
  materialResult.material_grade = ''
  materialResult.is_seismic = false
  materialResult.diameter = 0
  materialResult.raw_text = ''

  // 重置 CAD 解析状态
  cadFile.value = null
  cadPreview.value = null
  cadParsing.value = false
  cadParseHint.value = ''
  cadParseResult.success = false
  cadParseResult.component_type = ''
  cadParseResult.corner_bars = 0
  cadParseResult.middle_bars = 0
  cadParseResult.total_bars = 0
  cadParseResult.stirrup_dense = 0
  cadParseResult.stirrup_normal = 0
  cadParseResult.top_bars_total = 0
  cadParseResult.bottom_bars_total = 0
  cadParseResult.stirrup_legs = 0
  cadParseResult.design_spacing = 0

  nextTick(() => {
    const canvas = canvasRef.value
    if (canvas) {
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      canvas.width = 0
      canvas.height = 0
    }
  })
}

const handleFileChange = (file) => {
  const rawFile = file.raw || file
  imageFile.value = rawFile

  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target.result
    imgObj.value = new Image()
    imgObj.value.onload = () => {
      result.predictions = []
      result.detected_count = 0
      spacingResults.value = []
      complianceResult.status = null
      complianceResult.message = ''
      calibration.refBox = null
      calibration.pixelPerMm = 0
      nextTick(() => redrawCanvas())
    }
    imgObj.value.src = e.target.result
  }
  reader.readAsDataURL(rawFile)
}

// ---- CAD 截图上传与解析（Step 1）----
const handleCadFileChange = (file) => {
  const rawFile = file.raw || file
  cadFile.value = rawFile
  cadParseHint.value = ''

  const reader = new FileReader()
  reader.onload = (e) => {
    cadPreview.value = e.target.result
  }
  reader.readAsDataURL(rawFile)
}

// 将当前模式映射为后端 component_type
const componentTypeMap = {
  column_longitudinal: 'column',
  beam_longitudinal: 'beam',
  stirrup: 'beam',
  slab_wall: 'slab'
}

const parseCadImage = async () => {
  if (!cadFile.value) {
    ElMessage.warning('请先上传 CAD 截图')
    return
  }

  cadParsing.value = true
  cadParseHint.value = ''

  const compType = componentTypeMap[currentMode.value] || 'column'

  try {
    const formData = new FormData()
    formData.append('image', cadFile.value)
    formData.append('component_type', compType)

    const data = await api.parseCad(formData)

    if (data.success) {
      cadParseResult.success = true
      cadParseResult.component_type = compType

      // 按构件类型动态回填
      if (compType === 'column') {
        cadParseResult.corner_bars = data.corner_bars || 0
        cadParseResult.middle_bars = data.middle_bars || 0
        cadParseResult.total_bars = data.total_bars || 0
        cadParseResult.stirrup_dense = data.stirrup_dense || 0
        cadParseResult.stirrup_normal = data.stirrup_normal || 0
        pingfaParams.column.corner = data.corner_bars || 4
        pingfaParams.column.middle = data.middle_bars || 0
        cadParseHint.value = `✅ 角筋 ${data.corner_bars}，中部筋 ${data.middle_bars}，总 ${data.total_bars}，箍筋 ${data.stirrup_dense}/${data.stirrup_normal}`
      } else if (compType === 'beam') {
        cadParseResult.top_bars_total = data.top_bars_total || 0
        cadParseResult.bottom_bars_total = data.bottom_bars_total || 0
        cadParseResult.stirrup_dense = data.stirrup_dense || 0
        cadParseResult.stirrup_normal = data.stirrup_normal || 0
        cadParseResult.stirrup_legs = data.stirrup_legs || 0
        pingfaParams.beam.top = data.top_bars_total || 0
        pingfaParams.beam.bottom = data.bottom_bars_total || 0
        pingfaParams.stirrup.dense = data.stirrup_dense || 100
        pingfaParams.stirrup.normal = data.stirrup_normal || 200
        cadParseHint.value = `✅ 上部筋 ${data.top_bars_total}，下部筋 ${data.bottom_bars_total}，箍筋 ${data.stirrup_dense}/${data.stirrup_normal}`
      } else {
        cadParseResult.design_spacing = data.design_spacing || 0
        pingfaParams.slab.spacingX = data.design_spacing || 150
        pingfaParams.slab.spacingY = data.design_spacing || 150
        cadParseHint.value = `✅ 设计间距 ${data.design_spacing}mm`
      }
      ElMessage.success('CAD 图纸解析成功，参数已自动填充')
    } else {
      cadParseResult.success = false
      cadParseHint.value = `❌ 解析失败：${data.error || '未知错误'}`
      ElMessage.error('CAD 解析失败: ' + (data.error || '未知错误'))
    }
  } catch (error) {
    cadParseHint.value = `❌ 请求失败：${error.message}`
    ElMessage.error('CAD 解析请求失败: ' + error.message)
  } finally {
    cadParsing.value = false
  }
}

// ---- 原材微观核验 ----
const startMaterialVerify = async () => {
  if (!imageFile.value) {
    ElMessage.warning('请先上传钢筋特写照片')
    return
  }

  materialVerifying.value = true
  materialResult.success = false

  try {
    const formData = new FormData()
    formData.append('image', imageFile.value)

    const data = await api.verifyMaterial(formData)

    if (data.success) {
      materialResult.success = true
      materialResult.material_grade = data.material_grade || ''
      materialResult.is_seismic = data.is_seismic || false
      materialResult.diameter = data.diameter || 0
      materialResult.raw_text = data.raw_text || ''
      ElMessage.success('轧印识别成功')
    } else {
      ElMessage.error('识别失败: ' + (data.error || '未知错误'))
    }
  } catch (error) {
    ElMessage.error('请求失败: ' + error.message)
  } finally {
    materialVerifying.value = false
  }
}

// ---- Canvas 拖拽画框标定 ----
const handleMouseDown = (e) => {
  if (!imgObj.value || !needsCalibration.value) return

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
      const refLen = currentMode.value === 'material'
        ? materialParams.refLength
        : 100 // 默认标定宽度（用户可调整）
      calibration.pixelPerMm = pxW / refLen
      ElMessage.success(`标定完成: ${calibration.pixelPerMm.toFixed(3)} 像素/mm`)
    }
    redrawCanvas()
  }
}

// ---- 开始检测 ----
const startAnalysis = async () => {
  if (!imageFile.value) {
    ElMessage.warning('请先上传图片')
    return
  }

  isLoading.value = true
  spacingResults.value = []
  complianceResult.status = null
  complianceResult.message = ''

  try {
    const formData = new FormData()
    formData.append('image', imageFile.value)

    const extraParams = {}

    // 根据模式构建参数
    if (currentMode.value === 'stirrup' && calibration.pixelPerMm > 0) {
      extraParams.component_type = 'beam_column'
      extraParams.pixel_per_mm = calibration.pixelPerMm
      extraParams.tolerance = detectParams.tolerance
      extraParams.target_spacing_dense = pingfaParams.stirrup.dense
      extraParams.target_spacing_sparse = pingfaParams.stirrup.normal
    } else if (currentMode.value === 'slab_wall' && calibration.pixelPerMm > 0) {
      extraParams.component_type = 'slab_wall'
      extraParams.pixel_per_mm = calibration.pixelPerMm
      extraParams.tolerance = detectParams.tolerance
      extraParams.target_spacing = pingfaParams.slab.spacingX
    }

    const data = await api.analyze(
      formData,
      backendMode.value,
      detectParams.confidence,
      detectParams.overlap,
      extraParams
    )

    result.predictions = data.predictions || []
    result.detected_count = result.predictions.length
    result.image_url = data.image_url

    // 间距检测结果处理
    if (data.spacings) {
      spacingResults.value = data.spacings
      const passed = data.spacings.filter(s => s.status !== 'fail').length
      ElMessage.success(`检测完成 | 间距 ${data.spacings.length} 段，合格 ${passed} 段`)
    }
    // 纵筋合规判定
    else if (currentMode.value === 'column_longitudinal') {
      const aiCount = result.detected_count
      const expected = designTotal.value
      if (expected > 0) {
        if (aiCount < expected) {
          complianceResult.status = 'FAIL'
          complianceResult.message = `检测到 ${aiCount} 根纵筋，设计要求 ${expected} 根 → 缺少 ${expected - aiCount} 根纵筋`
        } else if (aiCount > expected) {
          complianceResult.status = 'WARNING'
          complianceResult.message = `检测到 ${aiCount} 根纵筋，设计要求 ${expected} 根 → 多出 ${aiCount - expected} 根钢筋`
        } else {
          complianceResult.status = 'PASS'
          complianceResult.message = `检测到 ${aiCount} 根纵筋，与设计值 ${expected} 完全一致`
        }
      } else {
        ElMessage.success(`检测完成，识别到 ${aiCount} 根钢筋`)
      }
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

// ---- Canvas 绘制 ----
const redrawCanvas = () => {
  const canvas = canvasRef.value
  if (!canvas || !imgObj.value) return

  const ctx = canvas.getContext('2d')
  canvas.width = imgObj.value.width
  canvas.height = imgObj.value.height
  ctx.drawImage(imgObj.value, 0, 0)

  // 参照物框
  if (calibration.refBox && calibration.refBox.w !== 0) {
    ctx.strokeStyle = '#ff9800'
    ctx.lineWidth = 3
    ctx.setLineDash([5, 5])
    ctx.strokeRect(calibration.refBox.x, calibration.refBox.y, calibration.refBox.w, calibration.refBox.h)
    ctx.setLineDash([])
    ctx.fillStyle = '#ff9800'
    ctx.font = '14px Arial'
    ctx.fillText('参照物', calibration.refBox.x, calibration.refBox.y - 5)
  }

  // 检测框
  ctx.strokeStyle = '#00e676'
  ctx.lineWidth = 2
  result.predictions.forEach((p, i) => {
    const x = p.x - p.width / 2
    const y = p.y - p.height / 2
    ctx.strokeRect(x, y, p.width, p.height)

    ctx.fillStyle = '#00e676'
    ctx.font = 'bold 12px Arial'
    ctx.fillText((i + 1).toString(), p.x - 4, p.y + 4)

    if (calibration.pixelPerMm > 0) {
      const dia = (Math.min(p.width, p.height) / calibration.pixelPerMm).toFixed(1)
      ctx.fillStyle = '#fff'
      ctx.font = '10px Arial'
      ctx.fillText(`φ${dia}`, x, y - 3)
    }
  })

  // 间距合规性线条
  if (spacingResults.value.length > 0) {
    spacingResults.value.forEach(sp => {
      const sx = sp.start.x, sy = sp.start.y
      const ex = sp.end.x, ey = sp.end.y
      const mx = (sx + ex) / 2, my = (sy + ey) / 2

      ctx.beginPath()
      ctx.strokeStyle = sp.color
      ctx.lineWidth = 3
      ctx.setLineDash([])
      ctx.moveTo(sx, sy)
      ctx.lineTo(ex, ey)
      ctx.stroke()

      const label = `${sp.mm_distance}mm`
      ctx.font = 'bold 13px Arial'
      const tw = ctx.measureText(label).width
      ctx.fillStyle = 'rgba(0,0,0,0.75)'
      ctx.fillRect(mx - tw / 2 - 4, my - 18, tw + 8, 20)

      ctx.fillStyle = sp.color
      ctx.textAlign = 'center'
      ctx.fillText(label, mx, my - 3)

      ctx.font = '10px Arial'
      ctx.fillText(sp.label, mx, my + 12)
      ctx.textAlign = 'start'
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
      inspection_type: currentMode.value,
      detected_count: result.detected_count,
      predictions: result.predictions,
      image_url: result.image_url
    })
    ElMessage.success('记录已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}
</script>

<template>
  <el-container class="workbench-container">
    <!-- ============ 侧边栏 ============ -->
    <el-aside width="380px" class="sidebar">
      <!-- 构件模式选择器 -->
      <el-card class="control-card mode-selector-card" :body-style="{ padding: '12px' }">
        <el-select
          v-model="currentMode"
          size="default"
          class="mode-select"
          placeholder="选择构件检测类型"
        >
          <el-option
            v-for="m in inspectionModes"
            :key="m.value"
            :value="m.value"
            :label="m.label"
          >
            <div class="mode-option">
              <el-icon :style="{ color: m.color }"><component :is="m.icon" /></el-icon>
              <span>{{ m.label }}</span>
            </div>
          </el-option>
        </el-select>
      </el-card>

      <!-- ===== Step 1: CAD 图纸解析（全局，material/material_vlm 除外） ===== -->
      <el-card v-if="!['material', 'material_vlm'].includes(currentMode)" class="control-card step-card" :body-style="{ padding: '12px' }">
        <template #header>
          <div class="card-header">
            <el-icon :style="{ color: '#E040FB' }"><Picture /></el-icon>
            <span>Step 1 · 图纸解析 (AI)</span>
          </div>
        </template>

        <div class="cad-section">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*"
            @change="handleCadFileChange"
            class="cad-upload-compact"
          >
            <el-button :type="cadFile ? 'success' : 'primary'" plain size="small" class="full-width">
              <el-icon class="el-icon--left"><Upload /></el-icon>
              {{ cadFile ? '已选择 CAD 截图' : '上传 CAD 截屏' }}
            </el-button>
          </el-upload>

          <el-button
            v-if="cadFile"
            type="primary"
            :loading="cadParsing"
            size="small"
            class="cad-parse-btn-compact"
            @click="parseCadImage"
          >
            {{ cadParsing ? '解析中...' : '智能提取' }}
          </el-button>
        </div>

        <div v-if="cadParseHint" class="compact-hint" :class="{ 'error': !cadParseResult.success }">
          {{ cadParseHint }}
        </div>

        <div v-if="cadParseResult.success && cadParseResult.stirrup_legs" class="ai-tag-row">
          <el-tag type="warning" size="small" effect="plain">
            AI 识别为 {{ cadParseResult.stirrup_legs }} 肢箍
          </el-tag>
        </div>
      </el-card>

      <!-- ===== 平法参数 — 动态表单 ===== -->
      <el-card v-if="!['material', 'material_vlm'].includes(currentMode)" class="control-card" :body-style="{ padding: '12px' }">
        <template #header>
          <div class="card-header">
            <el-icon :style="{ color: currentModeConfig.color }"><component :is="currentModeConfig.icon" /></el-icon>
            <span>平法参数 — {{ currentModeConfig.label.split(' - ')[1]?.split(' ')[0] || currentModeConfig.label }}</span>
          </div>
        </template>

        <!-- 柱纵筋 -->
        <div v-if="currentMode === 'column_longitudinal'" class="compact-form">
          <div v-if="cadParseResult.success && cadParseResult.component_type === 'column'" class="ai-fill-hint">
            <el-tag type="success" size="small" effect="plain">🤖 AI 已自动填充，可手动微调</el-tag>
          </div>
          <div class="form-row">
            <span class="label">角筋 (根)</span>
            <el-input-number v-model="pingfaParams.column.corner" :min="4" :max="20" :step="2" size="small" />
          </div>
          <div class="form-row">
            <span class="label">中部筋/边筋 (根)</span>
            <el-input-number v-model="pingfaParams.column.middle" :min="0" :max="30" :step="1" size="small" />
          </div>
          <div class="form-row total-row">
            <span class="label">设计总数</span>
            <span class="value">{{ designTotal }}</span>
          </div>
          <div v-if="cadParseResult.stirrup_dense" class="form-row stirrup-row">
            <span class="label">箍筋间距</span>
            <span class="value">{{ cadParseResult.stirrup_dense }}/{{ cadParseResult.stirrup_normal }}</span>
          </div>
        </div>

        <!-- 梁主筋 -->
        <div v-else-if="currentMode === 'beam_longitudinal'" class="compact-form">
          <div v-if="cadParseResult.success && cadParseResult.component_type === 'beam'" class="ai-fill-hint">
            <el-tag type="success" size="small" effect="plain">🤖 AI 已自动填充，可手动微调</el-tag>
          </div>
          <div class="form-row">
            <span class="label">上部纵筋 (根)</span>
            <el-input-number v-model="pingfaParams.beam.top" :min="0" :max="30" :step="1" size="small" />
          </div>
          <div class="form-row">
            <span class="label">下部纵筋 (根)</span>
            <el-input-number v-model="pingfaParams.beam.bottom" :min="0" :max="30" :step="1" size="small" />
          </div>
          <div class="form-row">
            <span class="label">腰筋 G/N (根)</span>
            <el-input-number v-model="pingfaParams.beam.waist" :min="0" :max="20" :step="1" size="small" />
          </div>
          <div class="form-row total-row">
            <span class="label">设计总数</span>
            <span class="value">{{ designTotal }}</span>
          </div>
          <div v-if="cadParseResult.stirrup_legs" class="form-row stirrup-row">
            <span class="label">箍筋</span>
            <span class="value">{{ cadParseResult.stirrup_dense }}/{{ cadParseResult.stirrup_normal }} ({{ cadParseResult.stirrup_legs }}肢)</span>
          </div>
        </div>

        <!-- 箍筋间距 -->
        <div v-else-if="currentMode === 'stirrup'" class="compact-form">
          <div v-if="cadParseResult.success" class="ai-fill-hint">
            <el-tag type="success" size="small" effect="plain">🤖 AI 已自动填充，可手动微调</el-tag>
          </div>
          <div v-else class="ai-fill-hint">
            <el-tag type="info" size="small" effect="plain">↑ 可通过 Step 1 上传 CAD 自动填充</el-tag>
          </div>
          <div class="form-row">
            <span class="label">加密区间距 (mm)</span>
            <el-input-number v-model="pingfaParams.stirrup.dense" :min="50" :max="300" :step="10" size="small" />
          </div>
          <div class="form-row">
            <span class="label">非加密区间距 (mm)</span>
            <el-input-number v-model="pingfaParams.stirrup.normal" :min="100" :max="500" :step="10" size="small" />
          </div>
          <div class="form-row">
            <span class="label">误差阈值 (mm)</span>
            <el-input-number v-model="detectParams.tolerance" :min="1" :max="50" :step="5" size="small" />
          </div>
        </div>

        <!-- 板/墙间距 -->
        <div v-else-if="currentMode === 'slab_wall'" class="compact-form">
          <div v-if="cadParseResult.success" class="ai-fill-hint">
            <el-tag type="success" size="small" effect="plain">🤖 AI 已自动填充，可手动微调</el-tag>
          </div>
          <div v-else class="ai-fill-hint">
            <el-tag type="info" size="small" effect="plain">↑ 可通过 Step 1 上传 CAD 自动填充</el-tag>
          </div>
          <div class="form-row">
            <span class="label">纵向设计间距 (mm)</span>
            <el-input-number v-model="pingfaParams.slab.spacingX" :min="50" :max="500" :step="10" size="small" />
          </div>
          <div class="form-row">
            <span class="label">横向设计间距 (mm)</span>
            <el-input-number v-model="pingfaParams.slab.spacingY" :min="50" :max="500" :step="10" size="small" />
          </div>
          <div class="form-row">
            <span class="label">误差阈值 (mm)</span>
            <el-input-number v-model="detectParams.tolerance" :min="1" :max="50" :step="5" size="small" />
          </div>
        </div>
      </el-card>

      <!-- ===== 进场原材参数 ===== -->
      <el-card v-if="currentMode === 'material'" class="control-card param-card">
        <template #header>
          <div class="card-header">
            <el-icon :style="{ color: '#F56C6C' }"><Box /></el-icon>
            <span>进场原材 — 标定参数</span>
          </div>
        </template>

        <el-form label-width="auto" label-position="top">
          <el-form-item>
            <template #label>
              <div class="param-label">
                <span>参照物宽度 (Reference Width)</span>
                <el-tag type="danger" size="small">mm</el-tag>
              </div>
            </template>
            <el-input-number
              v-model="materialParams.refLength"
              :min="1" :max="500" :step="0.1"
              :precision="1"
              controls-position="right"
              class="full-width"
            />
          </el-form-item>
        </el-form>

        <el-alert type="info" :closable="false" show-icon>
          上传图片后，在画布上<strong>拖拽画框</strong>框选参照物进行标定
        </el-alert>
      </el-card>

      <!-- ===== 通用检测参数 ===== -->
      <el-card class="control-card">
        <template #header>
          <div class="card-header">
            <el-icon><Setting /></el-icon>
            <span>AI 检测参数</span>
          </div>
        </template>
        <div class="param-item">
          <span>置信度阈值 ({{ detectParams.confidence }}%)</span>
          <el-slider v-model="detectParams.confidence" :min="10" :max="90" />
        </div>
      </el-card>

      <!-- ===== Step 2: 现场照片上传（非 material_vlm） ===== -->
      <el-card v-if="currentMode !== 'material_vlm'" class="control-card" :class="{ 'step-card': currentMode === 'column_longitudinal' }">
        <template #header>
          <div class="card-header">
            <el-icon><Camera /></el-icon>
            <span>{{ currentMode === 'column_longitudinal' ? 'Step 2 · 上传现场实拍图进行比对' : '图像上传' }}</span>
          </div>
        </template>

        <el-alert
          v-if="needsCalibration"
          type="info" :closable="false" show-icon class="mb-3"
        >
          上传图片后，可在画布上拖拽画框标定参照物
        </el-alert>

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

      <!-- ===== 原材微观核验专属区 ===== -->
      <el-card v-if="currentMode === 'material_vlm'" class="control-card step-card" :body-style="{ padding: '16px' }">
        <template #header>
          <div class="card-header">
            <el-icon :style="{ color: '#9C27B0' }"><View /></el-icon>
            <span>原材微观核验 — 轧印识别</span>
          </div>
        </template>

        <div class="vlm-hint">请上传钢筋表面带有轧制标志（如 4E22）的特写照片</div>

        <el-upload
          drag
          :auto-upload="false"
          :show-file-list="false"
          accept="image/*"
          @change="handleFileChange"
          class="vlm-upload"
        >
          <div v-if="imagePreview" class="vlm-preview">
            <img :src="imagePreview" class="vlm-preview-img" />
          </div>
          <div v-else>
            <el-icon class="el-icon--upload" :size="40"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽或 <em>点击上传</em> 钢筋特写</div>
          </div>
        </el-upload>

        <el-button
          type="primary"
          size="large"
          :loading="materialVerifying"
          :disabled="!imageFile"
          class="analyze-btn"
          @click="startMaterialVerify"
          style="margin-top: 12px"
        >
          <el-icon><MagicStick /></el-icon>
          {{ materialVerifying ? 'AI 识别中...' : '开始智能核验' }}
        </el-button>
      </el-card>

      <!-- 原材核验结果 -->
      <el-card v-if="currentMode === 'material_vlm' && materialResult.success" class="control-card result-card result-pass" :body-style="{ padding: '16px' }">
        <template #header>
          <div class="card-header">
            <el-icon :style="{ color: '#9C27B0' }"><DataAnalysis /></el-icon>
            <span>轧印识别结果</span>
          </div>
        </template>

        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="原始轧印">
            <el-tag type="danger" size="large" effect="dark">{{ materialResult.raw_text }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="钢筋牌号">
            <span class="desc-value">{{ materialResult.material_grade }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="抗震性能">
            <el-tag :type="materialResult.is_seismic ? 'success' : 'info'" effect="plain">
              {{ materialResult.is_seismic ? '✅ 满足抗震要求 (带E)' : '⚠️ 非抗震' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="公称直径">
            <span class="desc-value">{{ materialResult.diameter }} mm</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 开始检测（非 material_vlm） -->
      <el-button
        v-if="currentMode !== 'material_vlm'"
        type="primary"
        size="large"
        :loading="isLoading"
        :disabled="!imageFile"
        class="analyze-btn"
        @click="startAnalysis"
      >
        <el-icon><Lightning /></el-icon>
        {{ currentMode === 'column_longitudinal' || currentMode === 'beam_longitudinal' ? '比对' : '检测' }}
      </el-button>

      <!-- ===== 结果区域 ===== -->

      <!-- 纵筋合规判定 —— 对账单形式（柱+梁） -->
      <el-card
        v-if="['column_longitudinal', 'beam_longitudinal'].includes(currentMode) && complianceResult.status"
        class="result-card"
        :class="{
          'result-pass': complianceResult.status === 'PASS',
          'result-fail': complianceResult.status === 'FAIL',
          'result-warning': complianceResult.status === 'WARNING'
        }"
      >
        <template #header>
          <div class="card-header">
            <el-icon><DataAnalysis /></el-icon>
            <span>图模比对报告</span>
          </div>
        </template>

        <!-- 对账单明细 -->
        <div class="ledger-table">
          <div class="ledger-row">
            <span class="ledger-icon">📐</span>
            <span class="ledger-label">图纸要求总纵筋</span>
            <span class="ledger-value">{{ designTotal }} 根</span>
          </div>
          <div class="ledger-row">
            <span class="ledger-icon">📷</span>
            <span class="ledger-label">现场识别总纵筋</span>
            <span class="ledger-value">{{ result.detected_count }} 根</span>
          </div>
          <div class="ledger-divider"></div>
          <div class="ledger-row conclusion">
            <el-icon :size="24">
              <component :is="complianceResult.status === 'PASS' ? 'CircleCheck' : complianceResult.status === 'FAIL' ? 'CircleClose' : 'Warning'" />
            </el-icon>
            <span class="ledger-conclusion-text">
              {{ complianceResult.status === 'PASS' ? '✅ 图模一致，合规通过'
                : complianceResult.status === 'FAIL' ? '❌ 图模不一致，存在少筋风险'
                : '⚠️ 图模不一致，现场多于设计值' }}
            </span>
          </div>
        </div>

        <div class="compliance-message" style="margin-top: 12px">{{ complianceResult.message }}</div>
      </el-card>

      <!-- 间距检测结果 -->
      <el-card v-if="['stirrup', 'slab_wall'].includes(currentMode) && spacingResults.length" class="result-card result-pass">
        <template #header>
          <div class="card-header"><el-icon><DataAnalysis /></el-icon><span>间距检测结果</span></div>
        </template>
        <div class="result-stats">
          <div class="stat-item">
            <div class="stat-value">{{ result.detected_count }}</div>
            <div class="stat-label">检测数量</div>
          </div>
        </div>
        <div class="spacing-stats">
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
      </el-card>

      <!-- 通用计数结果 -->
      <el-card v-if="currentMode === 'material' && result.detected_count" class="result-card result-pass">
        <template #header>
          <div class="card-header"><el-icon><DataAnalysis /></el-icon><span>计数/直径检测结果</span></div>
        </template>
        <div class="result-stats">
          <div class="stat-item">
            <div class="stat-value">{{ result.detected_count }}</div>
            <div class="stat-label">检测数量</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ avgDiameter }}</div>
            <div class="stat-label">平均直径 (mm)</div>
          </div>
        </div>
      </el-card>

      <!-- 保存记录 -->
      <el-button
        v-if="result.detected_count"
        type="success"
        class="save-btn"
        @click="saveRecord"
      >
        <el-icon><Document /></el-icon> 保存记录
      </el-button>
    </el-aside>

    <!-- ============ 主内容区 ============ -->
    <el-main class="main-content">
      <div class="canvas-header">
        <h2>
          <span class="title-dot" :style="{ background: currentModeConfig.color }"></span>
          {{ currentModeConfig.label }}
          <el-tag :color="currentModeConfig.color" effect="dark" size="small">
            {{ backendMode === 'counting' ? 'Counting' : 'Spacing' }}
          </el-tag>
        </h2>
        <el-button text @click="router.push('/')">
          <el-icon><Back /></el-icon> 返回首页
        </el-button>
      </div>

      <div class="canvas-wrapper">
        <canvas
          ref="canvasRef"
          :style="{ cursor: needsCalibration ? 'crosshair' : 'default' }"
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove"
          @mouseup="handleMouseUp"
          @mouseleave="handleMouseUp"
        ></canvas>

        <div v-if="!imgObj" class="canvas-placeholder">
          <el-icon :size="64"><Picture /></el-icon>
          <p v-if="currentMode === 'column_longitudinal'">请上传柱截面图片</p>
          <p v-else-if="currentMode === 'material'">请上传钢筋端面图片</p>
          <p v-else-if="currentMode === 'material_vlm'">请在左侧上传钢筋轧印特写</p>
          <p v-else>请上传钢筋侧面/间距图片</p>
        </div>

        <!-- 标定状态 -->
        <div class="calibration-badge" v-if="needsCalibration && imgObj">
          <el-tag
            :type="calibration.pixelPerMm > 0 ? 'success' : 'warning'"
            effect="dark"
          >
            {{ calibration.pixelPerMm > 0
              ? `已标定: ${calibration.pixelPerMm.toFixed(2)} px/mm`
              : '请拖拽画框标定参照物'
            }}
          </el-tag>
        </div>

        <!-- 图例 -->
        <div class="legend-box" v-if="result.predictions.length">
          <div class="legend-item"><span class="dot" style="background:#00e676"></span>
            {{ spacingResults.length
              ? (currentMode === 'stirrup' ? '非加密区合格' : '合格')
              : '检测框'
            }}
          </div>
          <div class="legend-item" v-if="spacingResults.length && currentMode === 'stirrup'">
            <span class="dot" style="background:#00e5ff"></span>加密区合格
          </div>
          <div class="legend-item" v-if="spacingResults.length">
            <span class="dot" style="background:#ff1744"></span>不合格
          </div>
          <div class="legend-item" v-if="needsCalibration">
            <span class="dot" style="background:#ff9800"></span>参照物
          </div>
        </div>
      </div>
    </el-main>
  </el-container>
</template>

<style scoped>
.workbench-container {
  height: 100vh;
  background: #1a1c2c;
}

.sidebar {
  background: #2d3748;
  padding: 16px;
  overflow-y: auto;
}

/* 模式选择器 */
.mode-selector-card {
  border-left: 3px solid #409EFF;
}

.mode-select {
  width: 100%;
}

.mode-select :deep(.el-input__wrapper) {
  background-color: #22252b !important;
}

.mode-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 4px 0;
}

.mode-option-text {
  display: flex;
  flex-direction: column;
}

.mode-option-label {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.mode-option-desc {
  font-size: 11px;
  color: #718096;
  margin-top: 2px;
}

.mode-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 10px;
  background: rgba(0,0,0,0.2);
  border-radius: 6px;
}

.mode-hint-text {
  font-size: 12px;
  color: #a0aec0;
}

/* 参数卡片 */
.param-card {
  border-left: 3px solid transparent;
}

.control-card {
  margin-bottom: 12px;
  background: #3a4556;
  border: none;
}

.control-card :deep(.el-card__header) {
  padding: 10px 14px;
  background: #2d3748;
  border-bottom: 1px solid #4a5568;
}

.control-card :deep(.el-card__body) {
  padding: 14px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e2e8f0;
  font-weight: 600;
  font-size: 14px;
}

.param-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #cbd5e0;
  font-size: 13px;
}

.full-width {
  width: 100%;
}

/* 自动计算展示 */
.auto-calc-box {
  margin-top: 16px;
  padding: 14px;
  background: linear-gradient(135deg, #1a3a2a 0%, #22402d 100%);
  border-radius: 10px;
  border: 1px solid #38a169;
}

.calc-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.calc-label {
  color: #9ae6b4;
  font-size: 13px;
}

.calc-value {
  color: #68d391;
  font-size: 16px;
  font-weight: 600;
}

.calc-op {
  color: #4a9e6e;
  font-size: 14px;
  text-align: center;
  width: 100%;
}

.calc-divider {
  height: 1px;
  background: #38a169;
  margin: 6px 0;
}

.calc-row.total {
  padding-top: 6px;
}

.calc-total {
  color: #48bb78;
  font-size: 24px;
  font-weight: 700;
}

/* 参数 */
.param-item {
  margin-bottom: 12px;
}

.param-item span {
  display: block;
  color: #a0aec0;
  font-size: 13px;
  margin-bottom: 6px;
}

.mb-3 { margin-bottom: 12px; }

/* 按钮 */
.analyze-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  margin-bottom: 16px;
}

.save-btn {
  width: 100%;
  margin-bottom: 12px;
}

/* 结果卡片 */
.result-card { margin-bottom: 12px; }

.result-pass {
  background: linear-gradient(135deg, #1a4731 0%, #22543d 100%);
  border: 1px solid #38a169;
}

.result-fail {
  background: linear-gradient(135deg, #5c1127 0%, #822727 100%);
  border: 2px solid #e53e3e;
}

.result-warning {
  background: linear-gradient(135deg, #5c4813 0%, #744210 100%);
  border: 2px solid #d69e2e;
}

.result-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 12px;
}

.stat-item { flex: 1; text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: #68d391; }
.stat-label { font-size: 11px; color: #9ae6b4; }

.spacing-stats {
  margin-bottom: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.spacing-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
  font-size: 13px;
  color: #e2e8f0;
}

.spacing-stat-label { font-weight: 500; }
.spacing-stat-value { font-weight: 700; font-size: 15px; }

/* 合规判定 */
.compliance-result {
  text-align: center;
  padding: 16px 0;
}

.result-pass .compliance-result { color: #68d391; }
.result-fail .compliance-result { color: #fc8181; }
.result-warning .compliance-result { color: #f6e05e; }

.compliance-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin-top: 8px;
}

.compliance-message {
  font-size: 13px;
  color: #a0aec0;
  margin-top: 6px;
  line-height: 1.5;
}

/* 主内容区 */
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
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
}

.title-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
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
}

.canvas-placeholder {
  color: #4a5568;
  text-align: center;
}

.canvas-placeholder p {
  margin-top: 16px;
  font-size: 14px;
}

.calibration-badge {
  position: absolute;
  top: 16px;
  left: 16px;
}

.legend-box {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(0, 0, 0, 0.85);
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

.legend-item:last-child { margin-bottom: 0; }

.dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

/* ===== Step 卡片样式 ===== */
.step-card {
  border-left: 3px solid #E040FB;
}

.cad-upload {
  width: 100%;
}

.cad-upload :deep(.el-upload) {
  width: 100%;
}

.cad-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 16px;
  background: #22252b;
  border-color: #4a5568;
}

.cad-preview-box {
  max-height: 160px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cad-preview-img {
  max-width: 100%;
  max-height: 150px;
  border-radius: 6px;
}

.cad-parse-btn {
  width: 100%;
  margin-top: 10px;
}

.cad-hint {
  margin-top: 10px;
}

.stirrup-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(64, 158, 255, 0.12);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 6px;
  color: #79bbff;
  font-size: 13px;
}

/* ===== 对账单样式 ===== */
.ledger-table {
  padding: 8px 0;
}

.ledger-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 6px;
}

.ledger-row:not(.conclusion) {
  background: rgba(255, 255, 255, 0.04);
}

.ledger-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.ledger-label {
  flex: 1;
  color: #cbd5e0;
  font-size: 14px;
}

.ledger-value {
  font-size: 22px;
  font-weight: 700;
  color: #e2e8f0;
  font-variant-numeric: tabular-nums;
}

.ledger-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.12);
  margin: 10px 0;
}

.ledger-row.conclusion {
  padding: 12px;
  border-radius: 10px;
}

.result-pass .ledger-row.conclusion {
  background: rgba(72, 187, 120, 0.15);
}

.result-fail .ledger-row.conclusion {
  background: rgba(229, 62, 62, 0.15);
}

.result-warning .ledger-row.conclusion {
  background: rgba(214, 158, 46, 0.15);
}

.ledger-conclusion-text {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}
.cad-section {
  display: flex;
  gap: 8px;
  align-items: center;
}

.cad-upload-compact {
  flex: 1;
}

.full-width {
  width: 100%;
}

.cad-parse-btn-compact {
  width: 80px;
}

.compact-hint {
  font-size: 11px;
  color: #67C23A;
  margin-top: 6px;
  line-height: 1.3;
}

.compact-hint.error {
  color: #F56C6C;
}

.compact-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #cbd5e0;
}

.form-row .label {
  color: #909399;
}

.form-row.total-row {
  background: rgba(255, 255, 255, 0.05);
  padding: 6px 8px;
  border-radius: 4px;
  margin-top: 4px;
}

.form-row.total-row .value {
  color: #67C23A;
  font-weight: bold;
}

.form-row.stirrup-row {
  color: #409EFF;
  font-size: 12px;
}

.ai-tag-row {
  margin-top: 6px;
}

.vlm-hint {
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
  padding: 8px;
  background: rgba(156, 39, 176, 0.08);
  border-radius: 6px;
  border-left: 3px solid #9C27B0;
}

.vlm-upload {
  width: 100%;
}

.vlm-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  max-height: 200px;
  overflow: hidden;
}

.vlm-preview-img {
  max-width: 100%;
  max-height: 200px;
  border-radius: 6px;
}

.desc-value {
  font-weight: bold;
  font-size: 15px;
  color: #fff;
}

.ai-fill-hint {
  margin-bottom: 8px;
}
</style>

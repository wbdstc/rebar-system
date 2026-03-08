<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { marked } from 'marked'
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
    value: 'column_stirrup',
    label: '柱 - 箍筋检测 (KZ)',
    icon: 'Grid',
    color: '#409EFF',
    backendMode: 'spacing',
    desc: '检测柱箍筋间距，区分加密区与非加密区'
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
    value: 'beam_stirrup',
    label: '梁 - 箍筋检测 (KL)',
    icon: 'Grid',
    color: '#2196F3',
    backendMode: 'spacing',
    desc: '检测梁箍筋间距，区分加密区与非加密区'
  },
  {
    value: 'slab_mesh',
    label: '板 - 钢筋检测 (B)',
    icon: 'Grid',
    color: '#E6A23C',
    backendMode: 'spacing',
    desc: '检测楼板分布钢筋间距，比对设计间距'
  },
  {
    value: 'wall_mesh',
    label: '墙 - 钢筋检测 (Q)',
    icon: 'Grid',
    color: '#FF7043',
    backendMode: 'spacing',
    desc: '检测剪力墙分布筋间距，比对设计间距'
  },
]


// =============================================
// 状态定义
// =============================================

// =============================================
// Dashboard 导航与步骤状态
// =============================================

// =============================================
// 新手引导 (Tour) 状态
// =============================================
const showTour = ref(false)
const tourOpen = ref(false)
const tourStep1Ref = ref(null)
const tourStep2Ref = ref(null)
const tourStep3Ref = ref(null)

onMounted(() => {
  // 检查是否是首次进入
  const hasSeenTour = localStorage.getItem('hasSeenWorkBenchTour')
  if (!hasSeenTour) {
    setTimeout(() => {
      tourOpen.value = true
    }, 500)
  }
})

const onTourClose = () => {
  tourOpen.value = false
  localStorage.setItem('hasSeenWorkBenchTour', 'true')
}

const currentMenu = ref('column')
const activeStep = ref('step1')

const handleMenuSelect = (index) => {
  if (index === 'project') {
    router.push('/records')
    return
  }
  if (index === 'settings') {
    import('element-plus').then(({ ElMessage }) => {
      ElMessage.info('设置功能开发中...')
    })
    return
  }
  const modeMap = {
    'column': 'column_longitudinal',
    'beam': 'beam_longitudinal',
    'slab': 'slab_mesh',
    'wall': 'wall_mesh'
  }
  if (modeMap[index]) {
    currentMode.value = modeMap[index]
    currentMenu.value = index
  }
}

watch(currentMenu, (newMenu) => {
  if (newMenu === 'column' && !currentMode.value.startsWith('column')) {
    currentMode.value = 'column_longitudinal'
  } else if (newMenu === 'beam' && !currentMode.value.startsWith('beam')) {
    currentMode.value = 'beam_longitudinal'
  }
})

const currentMode = ref('column_longitudinal')
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
  slab: { bottomSpacing: 150, topSpacing: 150 },
  wall: { horizontalSpacing: 200, verticalSpacing: 200 }
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
const aiReport = ref('')  // AI 审图分析报告（Markdown 原文）
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

// AI 报告 HTML（由 marked 渲染）
const aiReportHtml = computed(() => {
  if (!aiReport.value) return ''
  return marked(aiReport.value)
})

watch(cadFile, (newVal) => {
  if (newVal && activeStep.value === 'step2') activeStep.value = 'step1'
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
  ['column_stirrup', 'beam_stirrup', 'slab_mesh', 'wall_mesh', 'material'].includes(currentMode.value)
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
  aiReport.value = ''
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

// 将当前模式映射为 VLM 后端 component_type（精准中文语义）
const vlmComponentLabel = () => {
  if (currentMode.value.startsWith('column')) return '柱'
  if (currentMode.value.startsWith('beam')) return '梁'
  if (currentMode.value === 'slab_mesh') return '楼板'
  if (currentMode.value === 'wall_mesh') return '剪力墙'
  return '柱'
}

// 后端 VLM 接口的 component_type 参数
const vlmComponentType = () => {
  if (currentMode.value.startsWith('column')) return 'column'
  if (currentMode.value.startsWith('beam')) return 'beam'
  if (currentMode.value === 'slab_mesh') return 'slab'
  if (currentMode.value === 'wall_mesh') return 'wall'
  return 'column'
}

const parseCadImage = async () => {
  if (!cadFile.value) {
    ElMessage.warning('请先上传 CAD 截图')
    return
  }

  cadParsing.value = true
  cadParseHint.value = ''
  aiReport.value = ''

  const compType = vlmComponentType()

  try {
    const formData = new FormData()
    formData.append('image', cadFile.value)
    formData.append('component_type', compType)

    const data = await api.parseCad(formData)

    if (data.success) {
      cadParseResult.success = true
    
    ElNotification({
      title: '图纸解析成功',
      message: '设计参数已自动填入上方配置面板，即将进入【现场比对】步骤。',
      type: 'success',
      duration: 4000
    })
    
    setTimeout(() => {
      activeStep.value = 'step2'
    }, 1500)
      cadParseResult.component_type = compType

      // 存储 AI 审图报告（Markdown）
      aiReport.value = data.report || ''

      // 从 extracted_data 或顶层字段提取数据（兼容新旧格式）
      const ed = data.extracted_data || data

      // 按构件类型动态回填（值为0表示图纸未标注，保留默认值）
      const v = (val) => val || 0  // 安全取值
      const label = (val) => val ? val : '图纸未标注'

      if (compType === 'column') {
        cadParseResult.corner_bars = v(ed.corner_bars)
        cadParseResult.middle_bars = v(ed.middle_bars)
        cadParseResult.total_bars = v(ed.total_bars)
        cadParseResult.stirrup_dense = v(ed.stirrup_dense)
        cadParseResult.stirrup_normal = v(ed.stirrup_normal)
        // 仅当 AI 返回非0时覆盖默认值
        if (ed.corner_bars) pingfaParams.column.corner = ed.corner_bars
        if (ed.middle_bars) pingfaParams.column.middle = ed.middle_bars
        if (ed.stirrup_dense) pingfaParams.stirrup.dense = ed.stirrup_dense
        if (ed.stirrup_normal) pingfaParams.stirrup.normal = ed.stirrup_normal
        cadParseHint.value = `✅ 角筋 ${label(ed.corner_bars)}，中部筋 ${label(ed.middle_bars)}，总 ${label(ed.total_bars)}，箍筋 ${label(ed.stirrup_dense)}/${label(ed.stirrup_normal)}`
      } else if (compType === 'beam') {
        cadParseResult.top_bars_total = v(ed.top_bars_total)
        cadParseResult.bottom_bars_total = v(ed.bottom_bars_total)
        cadParseResult.stirrup_dense = v(ed.stirrup_dense)
        cadParseResult.stirrup_normal = v(ed.stirrup_normal)
        cadParseResult.stirrup_legs = v(ed.stirrup_legs)
        if (ed.top_bars_total) pingfaParams.beam.top = ed.top_bars_total
        if (ed.bottom_bars_total) pingfaParams.beam.bottom = ed.bottom_bars_total
        if (ed.waist_bars) pingfaParams.beam.waist = ed.waist_bars
        if (ed.stirrup_dense) pingfaParams.stirrup.dense = ed.stirrup_dense
        if (ed.stirrup_normal) pingfaParams.stirrup.normal = ed.stirrup_normal
        cadParseHint.value = `✅ 上部筋 ${label(ed.top_bars_total)}，下部筋 ${label(ed.bottom_bars_total)}，箍筋 ${label(ed.stirrup_dense)}/${label(ed.stirrup_normal)}`
      } else if (compType === 'slab') {
        cadParseResult.design_spacing = v(ed.design_spacing)
        if (ed.design_spacing) {
          pingfaParams.slab.bottomSpacing = ed.design_spacing
          pingfaParams.slab.topSpacing = ed.design_spacing
        }
        cadParseHint.value = `✅ 楼板设计间距 ${label(ed.design_spacing)}`
      } else {
        // wall
        cadParseResult.design_spacing = v(ed.design_spacing)
        if (ed.design_spacing) {
          pingfaParams.wall.horizontalSpacing = ed.design_spacing
          pingfaParams.wall.verticalSpacing = ed.design_spacing
        }
        cadParseHint.value = `✅ 剪力墙设计间距 ${label(ed.design_spacing)}`
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

    // 根据模式构建参数 — CV 检测层向下兼容映射
    if ((currentMode.value === 'column_stirrup' || currentMode.value === 'beam_stirrup') && calibration.pixelPerMm > 0) {
      extraParams.component_type = 'beam_column'
      extraParams.pixel_per_mm = calibration.pixelPerMm
      extraParams.tolerance = detectParams.tolerance
      extraParams.target_spacing_dense = pingfaParams.stirrup.dense
      extraParams.target_spacing_sparse = pingfaParams.stirrup.normal
    } else if (currentMode.value === 'slab_mesh' && calibration.pixelPerMm > 0) {
      extraParams.component_type = 'slab_wall'
      extraParams.pixel_per_mm = calibration.pixelPerMm
      extraParams.tolerance = detectParams.tolerance
      extraParams.target_spacing = pingfaParams.slab.bottomSpacing
    } else if (currentMode.value === 'wall_mesh' && calibration.pixelPerMm > 0) {
      extraParams.component_type = 'slab_wall'
      extraParams.pixel_per_mm = calibration.pixelPerMm
      extraParams.tolerance = detectParams.tolerance
      extraParams.target_spacing = pingfaParams.wall.horizontalSpacing
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
  <el-container class="h-screen bg-slate-50 text-slate-800 relative flex flex-col overflow-hidden">
    <!-- 顶部导航栏 (工程蓝底色) -->
    <el-header class="relative z-20 flex justify-between items-center px-6 bg-blue-600 text-white shadow-md h-14 shrink-0">
      <div class="flex items-center gap-4">
        <el-button text class="!text-white hover:!bg-white/10" @click="router.push('/')">
          <el-icon class="mr-1 text-lg"><Back /></el-icon> 返回首页
        </el-button>
      </div>
      <div class="text-[17px] font-bold tracking-wider flex items-center gap-3">
        <span>智能审图工作台</span>
        <div class="w-1.5 h-1.5 rounded-full bg-white/60"></div>
        <span class="text-blue-100 font-medium">{{ currentModeConfig?.label || 'AI 钢筋智能检测' }}</span>
      </div>
      <div class="flex items-center gap-4">
        <el-button text class="!text-white hover:!bg-white/10">
          <el-icon class="mr-1 text-lg"><QuestionFilled /></el-icon> 帮助
        </el-button>
      </div>
    </el-header>

    <el-container class="relative z-10 overflow-hidden flex-1">
      <!-- 左侧导航栏 -->
      <el-aside width="200px" class="bg-blue-600 border-r border-blue-700 shadow-lg flex flex-col z-20">
        <div class="p-4 border-b border-blue-500/30 flex items-center gap-2 text-blue-100 text-xs font-bold uppercase tracking-wider">
          <el-icon><Menu /></el-icon> 验收模块
        </div>
        <el-menu
          :default-active="currentMenu"
          class="!border-r-0 bg-transparent flex-1 pt-2 w-full custom-left-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="project" class="menu-item-hover">
            <el-icon><List /></el-icon>
            <template #title>检测记录</template>
          </el-menu-item>
          
          <el-menu-item index="column" class="menu-item-hover">
            <el-icon><DataBoard /></el-icon>
            <template #title>柱检测</template>
          </el-menu-item>
          
          <el-menu-item index="beam" class="menu-item-hover">
            <el-icon><TopRight /></el-icon>
            <template #title>梁检测</template>
          </el-menu-item>
          
          <el-menu-item index="slab" class="menu-item-hover">
            <el-icon><Grid /></el-icon>
            <template #title>板检测</template>
          </el-menu-item>
          
          <el-menu-item index="wall" class="menu-item-hover">
            <el-icon><Histogram /></el-icon>
            <template #title>墙检测</template>
          </el-menu-item>



          <el-menu-item index="settings" class="menu-item-hover" style="margin-top: auto; border-top: 1px solid rgba(255,255,255,0.1);">
            <el-icon><Setting /></el-icon>
            <template #title>个人设置</template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-tour v-model="tourOpen" @close="onTourClose">
        <el-tour-step :target="tourStep1Ref" title="第一步：配置参数" description="在这里通过手动输入或者 AI 图纸解析（下一步），配置当前构件的设计配筋参数。" />
        <el-tour-step :target="tourStep2Ref" title="第二步：控制流程" description="在顶部切换【解析图纸】和【现场比对】模块。我们建议先解析图纸，再上传照片进行现场比对验证。" />
        <el-tour-step :target="tourStep3Ref" title="第三步：上传与分析" description="在工作区域拖拽或点击上传您的 CAD 截图或实景照片。系统会自动分析并生成合规性账单。" />
      </el-tour>

      <!-- 主工作区 -->
      <el-main class="bg-cad-grid p-6 flex flex-col gap-5 overflow-y-auto w-full">
        <!-- 顶部：参数配置卡片 -->
        <el-card ref="tourStep1Ref" class="dashboard-card shrink-0 shadow-sm border-slate-200 mb-5" :body-style="{ padding: '16px 24px' }">
          <div class="flex flex-col xl:flex-row gap-8 items-start xl:items-center">
            
            <!-- 平法参数 (Left side) -->
            <div class="flex-1 xl:border-r border-slate-200 xl:pr-8 flex flex-col justify-center">
              
              <div class="flex items-center gap-6 mb-4">
                <div class="flex items-center gap-2 text-slate-800 font-bold text-base whitespace-nowrap">
                  <el-icon class="text-blue-500"><EditPen /></el-icon> 📝 检测参数与要求
                </div>
                <!-- 检测子模式切换器 (Radio) -->
                <div class="flex-1">
                  <el-radio-group v-if="currentMenu === 'column'" v-model="currentMode" size="default">
                    <el-radio-button value="column_longitudinal">纵筋 (计数)</el-radio-button>
                    <el-radio-button value="column_stirrup">箍筋 (间距)</el-radio-button>
                  </el-radio-group>
                  <el-radio-group v-else-if="currentMenu === 'beam'" v-model="currentMode" size="default">
                    <el-radio-button value="beam_longitudinal">主筋 (计数)</el-radio-button>
                    <el-radio-button value="beam_stirrup">箍筋 (间距)</el-radio-button>
                  </el-radio-group>
                  <el-radio-group v-else-if="currentMenu === 'material'" v-model="currentMode" size="default">
                    <el-radio-button value="material">截面计数拉拔</el-radio-button>
                    <el-radio-button value="material_vlm">AI微观表面识别</el-radio-button>
                  </el-radio-group>
                  <el-tag v-else type="primary" effect="plain" class="border-blue-200">
                    {{ backendMode === 'counting' ? '计数检测' : '间距检测' }}
                  </el-tag>
                </div>
              </div>

              <!-- 动态表单 -->
              <div class="bg-slate-50/50 border border-slate-100 rounded-xl p-4 w-full">
                
                <!-- 柱纵筋 -->
                <template v-if="currentMode === 'column_longitudinal'">
                  <div class="grid grid-cols-2 gap-5 w-full xl:w-4/5">
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">角筋数量 (根)</span>
                      <el-input-number v-model="pingfaParams.column.corner" :min="4" :max="20" :step="2" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">中部/边筋数量 (根)</span>
                      <el-input-number v-model="pingfaParams.column.middle" :min="0" :max="30" :step="1" class="!w-full" controls-position="right" />
                    </div>
                  </div>
                  <div class="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between w-full xl:w-4/5">
                    <span class="text-slate-600 text-sm font-bold">设计总数预估</span>
                    <div class="text-emerald-500 text-3xl font-black tabular-nums">{{ designTotal }}</div>
                  </div>
                </template>

                <!-- 梁主筋 -->
                <template v-else-if="currentMode === 'beam_longitudinal'">
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-5 w-full">
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">上部纵筋 (根)</span>
                      <el-input-number v-model="pingfaParams.beam.top" :min="0" :max="30" :step="1" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">下部纵筋 (根)</span>
                      <el-input-number v-model="pingfaParams.beam.bottom" :min="0" :max="30" :step="1" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">腰筋 G/N (根)</span>
                      <el-input-number v-model="pingfaParams.beam.waist" :min="0" :max="20" :step="1" class="!w-full" controls-position="right" />
                    </div>
                  </div>
                  <div class="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between w-full">
                    <span class="text-slate-600 text-sm font-bold">设计总数预估</span>
                    <div class="text-emerald-500 text-3xl font-black tabular-nums">{{ designTotal }}</div>
                  </div>
                </template>

                <!-- 柱/梁 箍筋 -->
                <template v-else-if="['column_stirrup', 'beam_stirrup'].includes(currentMode)">
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-5 w-full mt-1">
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">加密区间距 (mm)</span>
                      <el-input-number v-model="pingfaParams.stirrup.dense" :min="50" :max="300" :step="10" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">非加密区间距 (mm)</span>
                      <el-input-number v-model="pingfaParams.stirrup.normal" :min="100" :max="500" :step="10" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">误差阈值 (mm)</span>
                      <el-input-number v-model="detectParams.tolerance" :min="1" :max="50" :step="5" class="!w-full" controls-position="right" />
                    </div>
                  </div>
                </template>

                <!-- 板钢筋间距 -->
                <template v-else-if="currentMode === 'slab_mesh'">
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-5 w-full mt-1">
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">底筋间距 (mm)</span>
                      <el-input-number v-model="pingfaParams.slab.bottomSpacing" :min="50" :max="500" :step="10" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">负筋/面筋间距 (mm)</span>
                      <el-input-number v-model="pingfaParams.slab.topSpacing" :min="50" :max="500" :step="10" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">误差阈值 (mm)</span>
                      <el-input-number v-model="detectParams.tolerance" :min="1" :max="50" :step="5" class="!w-full" controls-position="right" />
                    </div>
                  </div>
                </template>

                <!-- 墙钢筋间距 -->
                <template v-else-if="currentMode === 'wall_mesh'">
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-5 w-full mt-1">
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">水平间距 (mm)</span>
                      <el-input-number v-model="pingfaParams.wall.horizontalSpacing" :min="50" :max="500" :step="10" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">竖向间距 (mm)</span>
                      <el-input-number v-model="pingfaParams.wall.verticalSpacing" :min="50" :max="500" :step="10" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">误差阈值 (mm)</span>
                      <el-input-number v-model="detectParams.tolerance" :min="1" :max="50" :step="5" class="!w-full" controls-position="right" />
                    </div>
                  </div>
                </template>

                <!-- 原材计数尺寸 -->
                <template v-else-if="currentMode === 'material'">
                  <div class="flex flex-col gap-4 w-full">
                    <div class="flex flex-col gap-2 xl:w-1/2">
                      <span class="text-slate-500 text-[13px] font-medium">参照物标定宽度 (mm)</span>
                      <el-input-number v-model="materialParams.refLength" :min="1" :max="500" :step="0.1" :precision="1" class="!w-full" controls-position="right" />
                    </div>
                    <div class="text-[13px] text-orange-500 flex items-center gap-2 bg-orange-50 px-4 py-2.5 rounded-lg border border-orange-100">
                      <el-icon class="text-lg"><InfoFilled /></el-icon> 提示: 请在下方画布框选已知参照物（标准名片/卡牌通常为85.6mm宽）
                    </div>
                  </div>
                </template>
                
                <!-- 微观 AI 识别 -->
                <template v-else-if="currentMode === 'material_vlm'">
                  <div class="w-full text-sm text-purple-700 bg-purple-50 p-4 rounded-xl border border-purple-100 flex items-start gap-3 shadow-sm">
                    <el-icon class="mt-0.5 text-xl"><Opportunity /></el-icon>
                    <div class="leading-relaxed">
                      <strong class="text-purple-800 text-base">微观标牌语义识别</strong><br/>
                      <span class="text-purple-600/90">结合大语言与视觉大模型，自动锁定并提取钢筋端面轧制标识（如 4E 22）。无需手工录入参数，自动比对截面直径、牌号级别与抗震要求（E）。</span>
                    </div>
                  </div>
                </template>

              </div>
            </div>

            <!-- AI Params (Right side) -->
            <div class="w-full xl:w-96 shrink-0 flex flex-col justify-center">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2 text-slate-800 font-bold text-base">
                  <el-icon class="text-indigo-500"><Setting /></el-icon> 🤖 AI 检测控制中心
                </div>
                <el-tag v-if="calibration.pixelPerMm > 0" type="success" effect="plain" size="small" class="border-green-200">
                  <el-icon class="mr-1"><Tools /></el-icon> 标定 {{ calibration.pixelPerMm.toFixed(1) }}px/mm
                </el-tag>
              </div>

              <div class="bg-indigo-50/50 p-4 rounded-xl border border-indigo-100">
                <div class="flex justify-between items-center text-[13px] text-slate-600 mb-2">
                  <span class="font-medium">计算机视觉模型置信度阈值</span>
                  <span class="font-black text-indigo-600 text-lg tabular-nums leading-none"><span class="text-sm">≥</span> {{ detectParams.confidence }}<span class="text-xs font-normal text-indigo-400 ml-0.5">%</span></span>
                </div>
                <el-slider v-model="detectParams.confidence" :min="10" :max="90" class="custom-slider !mb-1" />
              </div>

              <div v-if="cadParseResult.success && !['material', 'material_vlm'].includes(currentMode)" class="mt-3 p-2.5 bg-green-50 rounded-lg border border-green-100 text-[13px] text-green-700 flex items-start gap-1.5 shadow-sm">
                <el-icon class="mt-0.5"><CircleCheckFilled /></el-icon>
                <span class="leading-tight">图纸配筋参数已由 AI 成功解析并导入。</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 底部：上传与比对卡片 -->
        <el-card class="dashboard-card flex-1 flex flex-col min-h-[400px] shadow-sm border-slate-200" :body-style="{ padding: '0', display: 'flex', flexDirection: 'column', height: '100%' }">
          
          <!-- 卡片头部工作流步骤栏 -->
          <div class="px-5 py-3 border-b border-slate-100 flex justify-between items-center shrink-0 bg-white">
            <el-radio-group ref="tourStep2Ref" v-model="activeStep" size="large" class="step-radio-group shadow-sm rounded-lg overflow-hidden">
              <el-radio-button value="step1" v-if="!['material', 'material_vlm'].includes(currentMode)">
                步骤 1: 解析图纸
              </el-radio-button>
              <el-radio-button value="step2">
                {{ ['material', 'material_vlm'].includes(currentMode) ? '▶ 上传并检测' : '▶ 步骤 2: 现场比对' }}
              </el-radio-button>
            </el-radio-group>
            
            <div class="flex items-center gap-4">
              <!-- Result / State Badges -->
              <el-tag v-if="complianceResult.status === 'PASS'" type="success" effect="dark" size="default" class="mr-2 px-4 shadow-sm border-0"><el-icon class="mr-1"><CircleCheckFilled /></el-icon> 图模一致，合规通过</el-tag>
              <el-tag v-else-if="complianceResult.status === 'FAIL'" type="danger" effect="dark" size="default" class="mr-2 px-4 shadow-sm border-0"><el-icon class="mr-1"><Warning /></el-icon> 图模不一致 (存在少筋)</el-tag>
              <el-tag v-else-if="complianceResult.status === 'WARNING'" type="warning" effect="dark" size="default" class="mr-2 px-4 shadow-sm border-0"><el-icon class="mr-1"><Warning /></el-icon> 图模不一致 (现场多筋)</el-tag>
              <el-tag v-else-if="result.detected_count || materialResult.success" type="success" effect="dark" size="default" class="mr-2 px-4 shadow-sm border-0"><el-icon class="mr-1"><CircleCheckFilled /></el-icon> 检测完成</el-tag>

               <el-button
                 v-if="activeStep === 'step1'"
                 type="primary"
                 :loading="cadParsing"
                 loading-icon="Loading"
                 loading-text="正在智能解析图纸中..."
                 :disabled="!cadFile"
                 class="px-8 shadow-md !text-sm font-bold tracking-wide"
                 style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); border: none;"
                 @click="parseCadImage"
               >
                 <el-icon class="mr-2"><Cpu /></el-icon>
                 智能解析参数
               </el-button>
               
               <el-button
                 v-else
                 type="primary"
                 :loading="isLoading || materialVerifying"
                 loading-icon="Loading"
                 loading-text="云端大模型计算中..."
                 :disabled="!imageFile"
                 class="px-8 shadow-md !text-sm font-bold tracking-wide"
                 style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); border: none;"
                 @click="currentMode === 'material_vlm' ? startMaterialVerify() : startAnalysis()"
               >
                 <el-icon class="mr-2"><Lightning /></el-icon>
                 开始验证计算
               </el-button>
            </div>
          </div>

          <!-- 卡片内容体：CAD或现场上传工作区 -->
          <div ref="tourStep3Ref" class="flex-1 relative bg-cad-grid overflow-hidden flex min-h-[400px]">
            
            <!-- Step 1 View: CAD Upload & Report -->
            <div v-show="activeStep === 'step1'" class="absolute inset-0 flex">
              <!-- 右侧或中心的图纸上传区 -->
              <div class="flex-1 p-6 flex flex-col h-full items-center justify-center border-r border-slate-200 overflow-y-auto">
                <div class="w-full max-w-2xl h-full flex flex-col items-center justify-center">
                  <el-upload
                    drag
                    :auto-upload="false"
                    :show-file-list="false"
                    accept="image/*"
                    @change="handleCadFileChange"
                    class="dashboard-upload w-full h-full text-center flex items-center justify-center flex-col"
                  >
                    <div v-if="cadPreview" class="w-full h-full rounded overflow-hidden flex items-center justify-center bg-transparent border border-slate-200 shadow-sm mx-auto p-2">
                       <img :src="cadPreview" class="max-h-[300px] max-w-full object-contain" />
                    </div>
                    <div v-else class="py-24 flex flex-col items-center justify-center">
                      <el-icon :size="72" class="text-blue-200 drop-shadow-sm mb-4"><DocumentCopy /></el-icon>
                      <div class="el-upload__text text-slate-500 font-medium text-lg mt-4">
                        将设计图纸 (CAD/PDF截图) 拖拽至此，或 <em class="text-blue-600 font-bold">点击上传</em>
                      </div>
                    </div>
                  </el-upload>
                </div>
              </div>
              
              <!-- CAD 解析报告区 -->
              <div class="w-96 bg-white flex flex-col h-full border-l border-slate-200 shrink-0">
                <div class="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50 shrink-0">
                  <div class="font-bold flex items-center gap-2 text-slate-800"><el-icon class="text-purple-500"><Document /></el-icon> 智能审图专家报告</div>
                </div>
                <div class="flex-1 p-4 overflow-y-auto">
                  <div v-if="aiReport" class="ai-report-content text-slate-600" v-html="aiReportHtml"></div>
                  <div v-else class="text-center text-slate-400 mt-20 flex flex-col gap-3 items-center">
                    <el-icon :size="48" class="text-slate-200"><DocumentCopy /></el-icon>
                    <div class="text-sm">上传图纸并解析后<br/>在此展示详细结构说明</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Step 2 View: Camera/Picture Upload -->
            <div v-show="activeStep === 'step2'" class="absolute inset-0 flex">
              <div class="flex-1 relative overflow-hidden" style="background-color: #eaeff5; background-image: radial-gradient(#d1d5db 1px, transparent 1px); background-size: 20px 20px;">
                
                <!-- 拖拽上传空状态 -->
                <div v-show="!imgObj" class="absolute inset-0 flex flex-col items-center justify-center p-8 z-10">
                  <div class="w-full max-w-3xl h-full max-h-[400px]">
                    <el-upload
                      drag
                      :auto-upload="false"
                      :show-file-list="false"
                      accept="image/*"
                      @change="handleFileChange"
                      class="dashboard-upload w-full h-full flex items-center justify-center flex-col bg-white/60 backdrop-blur-sm border-2 border-dashed border-blue-300 rounded-2xl shadow-sm hover:border-blue-500 hover:bg-white/80 transition-all"
                    >
                      <div v-if="imagePreview && currentMode === 'material_vlm'" class="h-full w-full flex items-center justify-center bg-transparent p-4">
                          <img :src="imagePreview" class="max-h-full max-w-full rounded-lg shadow-lg" />
                      </div>
                      <div v-else class="w-full h-full flex flex-col items-center justify-center py-16">
                        <div class="w-24 h-24 mb-6 rounded-full bg-blue-50 flex items-center justify-center shadow-inner border border-blue-100">
                           <el-icon :size="48" class="text-blue-500"><Camera /></el-icon>
                        </div>
                        <p class="text-slate-700 font-bold text-xl mb-2">
                          <span v-if="currentMode === 'column_longitudinal'">上传柱截面现场图像</span>
                          <span v-else-if="currentMode === 'material'">上传进场钢筋端面图</span>
                          <span v-else-if="currentMode === 'material_vlm'">上传带有轧印面 (如 4E 22) 的特写原图</span>
                          <span v-else>上传并拖拽施工现场图像</span>
                        </p>
                        <p class="text-slate-500 text-sm font-medium">系统将自动运行 CV 大模型比对合规性，支持快捷键粘贴照片</p>
                      </div>
                    </el-upload>
                  </div>
                </div>

                <!-- 结果画板区 (只要有图片就直接显示) -->
                <div v-show="imgObj" class="absolute inset-0 w-full h-full flex items-center justify-center p-4 z-20 overflow-auto">
                  <!-- 画板 -->
                  <canvas
                    ref="canvasRef"
                    class="rounded shadow-xl bg-white max-w-full"
                    :style="{ cursor: needsCalibration ? 'crosshair' : 'default', minWidth: '400px', objectFit: 'contain' }"
                    @mousedown="handleMouseDown"
                    @mousemove="handleMouseMove"
                    @mouseup="handleMouseUp"
                    @mouseleave="handleMouseUp"
                  ></canvas>

                  <!-- 重新上传按钮 (悬浮) -->
                  <div class="absolute top-6 left-6 flex gap-2 z-30">
                    <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" @change="handleFileChange">
                      <el-button size="default" class="shadow-md bg-white text-slate-700 hover:text-blue-500 border-0">
                        <el-icon class="mr-1 font-bold text-lg"><RefreshRight /></el-icon> 重置与更换
                      </el-button>
                    </el-upload>
                  </div>

                  <!-- 图例说明箱 -->
                  <div class="absolute top-6 right-6 bg-white/95 backdrop-blur-md border border-slate-200 p-4 rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] min-w-[180px] z-30 transform transition-all" v-if="(result.predictions && result.predictions.length) || materialResult.success || (complianceResult.status)">
                    <div class="text-xs font-bold text-slate-800 border-b border-slate-100 pb-2 mb-3 tracking-widest uppercase">
                       <el-icon class="mr-1 align-text-bottom"><InfoFilled/></el-icon> 结果与图例
                    </div>
                    
                    <template v-if="currentMode === 'material_vlm'">
                       <div class="text-sm">
                         <div class="flex justify-between mb-2"><span class="text-slate-500">识别牌号</span> <strong class="text-emerald-600 bg-emerald-50 px-2 rounded">{{ materialResult.material_grade }}</strong></div>
                         <div class="flex justify-between mb-2"><span class="text-slate-500">带E抗震</span> <strong :class="materialResult.is_seismic ? 'text-emerald-600 bg-emerald-50' : 'text-orange-500 bg-orange-50'" class="px-2 rounded">{{ materialResult.is_seismic ? '满足' : '未满足' }}</strong></div>
                         <div class="flex justify-between"><span class="text-slate-500">公称直径</span> <strong class="text-emerald-600 bg-emerald-50 px-2 rounded">{{ materialResult.diameter }}mm</strong></div>
                       </div>
                    </template>
                    <template v-else>
                      <!-- Count Stats if Longitudinal or Material -->
                      <div class="mb-3 border-b border-slate-100 pb-3" v-if="['column_longitudinal', 'beam_longitudinal', 'material'].includes(currentMode)">
                         <div class="flex justify-between items-center text-sm mb-1">
                           <span class="text-slate-500">检测件数</span>
                           <span class="font-black text-emerald-600 text-lg tabular-nums">{{ result.detected_count }}</span>
                         </div>
                         <div class="flex justify-between items-center text-sm" v-if="currentMode === 'material'">
                           <span class="text-slate-500">平均直径</span>
                           <span class="font-bold text-slate-800 tabular-nums">{{ avgDiameter }} mm</span>
                         </div>
                      </div>
                      
                      <!-- Legend Colors -->
                      <div class="flex items-center gap-2 text-xs text-slate-600 mb-2 font-medium">
                        <span class="w-3 h-3 rounded bg-[#00e676] shadow-sm"></span> 
                        {{ spacingResults.length ? (['column_stirrup', 'beam_stirrup'].includes(currentMode) ? '非加密区合格' : '合格') : '系统检测框' }}
                      </div>
                      <div class="flex items-center gap-2 text-xs text-slate-600 mb-2 font-medium" v-if="spacingResults.length && ['column_stirrup', 'beam_stirrup'].includes(currentMode)">
                        <span class="w-3 h-3 rounded bg-[#00e5ff] shadow-sm"></span>加密区合格
                      </div>
                      <div class="flex items-center gap-2 text-xs text-slate-600 mb-2 font-medium" v-if="spacingResults.length">
                        <span class="w-3 h-3 rounded bg-[#ff1744] shadow-sm"></span>超限误差段
                      </div>
                      <div class="flex items-center gap-2 text-xs text-slate-600 font-medium" v-if="needsCalibration">
                        <span class="w-3 h-3 rounded bg-[#ff9800] border border-orange-400 shadow-sm border-dashed"></span>尺寸标定框
                      </div>
                    </template>
                    
                    <!-- 保存结果按钮 -->
                    <el-button v-if="result.detected_count || materialResult.success" type="success" size="default" class="w-full mt-4 font-bold shadow-md shadow-emerald-500/20" @click="saveRecord">
                      <el-icon class="mr-1 text-base"><DocumentChecked /></el-icon> 提取并入库
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-card>

      </el-main>
    </el-container>
  </el-container>
</template>


<style scoped>
/* 轻量主题 CSS 覆写 */

/* CAD 网格背景底纹 */
.bg-cad-grid {
  background-color: #f8fafc;
  background-image: linear-gradient(rgba(59, 130, 246, 0.05) 1px, transparent 1px),
  linear-gradient(90deg, rgba(59, 130, 246, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
}

/* 侧边栏菜单样式适配蓝底 */
.custom-left-menu {
  border-right: none !important;
}

.menu-item-hover {
  margin: 4px 12px;
  border-radius: 8px;
  height: 44px;
  line-height: 44px;
  color: #bfdbfe !important; /* text-blue-200 */
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.menu-item-hover :deep(i) {
  color: #bfdbfe;
}

.menu-item-hover:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: #ffffff !important;
}

.menu-item-hover.is-active {
  background-color: #ffffff !important;
  color: #2563eb !important; /* text-blue-600 */
  font-weight: 600;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.menu-item-hover.is-active :deep(i) {
  color: #2563eb !important;
}

/* 卡片阴影与圆角 */
.dashboard-card {
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.03);
  transition: box-shadow 0.3s ease;
}

.dashboard-card:hover {
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
}

.dashboard-card :deep(.el-card__body) {
  height: 100%;
}

/* 按钮点击动效 */
.el-button {
  transition: transform 0.1s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s ease;
}
.el-button:active {
  transform: scale(0.96);
}

/* 输入框 Hover / Focus 状态增强 */
:deep(.el-input-number:hover .el-input__wrapper),
:deep(.el-input:hover .el-input__wrapper) {
  box-shadow: 0 0 0 1px #93c5fd inset !important; /* blue-300 */
}

:deep(.el-input-number .el-input__wrapper.is-focus),
:deep(.el-input .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #3b82f6 inset !important; /* blue-500 */
  background-color: #ffffff !important;
}

.form-row-dashboard {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.custom-slider :deep(.el-slider__bar) {
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
}

.custom-slider :deep(.el-slider__button) {
  border-color: #8b5cf6;
}

.step-radio-group {
  background: #f1f5f9;
  padding: 4px;
}

.step-radio-group :deep(.el-radio-button__inner) {
  border: none !important;
  background: transparent;
  color: #64748b;
  font-weight: bold;
  padding: 8px 24px;
  border-radius: 6px !important;
  box-shadow: none !important;
}

.step-radio-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #ffffff !important;
  color: #2563eb !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
}

.dashboard-upload {
  width: 100%;
  height: 100%;
}

.dashboard-upload :deep(.el-upload) {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.dashboard-upload :deep(.el-upload-dragger) {
  background: transparent;
  border: none;
  padding: 0;
  width: 100%;
  height: 100%;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.dashboard-upload.is-dragover :deep(.el-upload-dragger) {
  background: rgba(255,255,255,0.8);
  border: 2px dashed #3b82f6;
}

/* AI 审图报告特定样式重建 (轻量主题) */
.ai-report-content {
  font-size: 13px;
  line-height: 1.6;
}

.ai-report-content :deep(h2) {
  font-size: 15px;
  font-weight: bold;
  color: #334155;
  margin-top: 12px;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e2e8f0;
}

.ai-report-content :deep(h3) {
  font-size: 14px;
  font-weight: bold;
  color: #475569;
  margin-top: 10px;
  margin-bottom: 6px;
}

.ai-report-content :deep(p) {
  margin-bottom: 8px;
  color: #64748b;
}

.ai-report-content :deep(ul) {
  padding-left: 20px;
  margin-bottom: 8px;
  color: #64748b;
}

.ai-report-content :deep(li) {
  margin-bottom: 4px;
}

.ai-report-content :deep(strong) {
  color: #2563eb;
}
</style>

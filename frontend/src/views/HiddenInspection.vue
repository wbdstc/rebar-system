<script setup>
import { ref, reactive, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()

// =============================================
// 全局共享状态
// =============================================
const activeTab = ref('spacing')  // spacing | column
const isLoading = ref(false)
const imageFile = ref(null)
const imagePreview = ref(null)
const canvasRef = ref(null)
const imgObj = ref(null)

// =============================================
// Tab 1: 间距与箍筋检测
// =============================================
const componentType = ref('slab_wall')  // slab_wall | beam_column
const spacingParams = reactive({
  designSpacing: 150,
  denseSpacing: 100,
  sparseSpacing: 200,
  tolerance: 20
})
const spacingResults = ref([])

const spacingDetectParams = reactive({
  confidence: 40,
  overlap: 40,
  refLength: 85.6
})

const spacingResult = reactive({
  predictions: [],
  detected_count: 0,
  image_url: null
})

const spacingCalibration = reactive({
  isDrawing: false,
  startX: 0, startY: 0,
  refBox: null,
  pixelPerMm: 0
})

// =============================================
// Tab 2: 柱截面合规检测
// =============================================
const columnInfo = reactive({
  columnId: 'KZ1',
  sectionWidth: 650,
  sectionHeight: 600,
  hoopSpacing: 100
})

const rebarConfig = ref([])
const rebarInput = ref('')

const columnResult = reactive({
  predictions: [],
  detected_count: 0,
  hoop_path: [],
  inner_ties: [],
  image_url: null
})

const columnCalibration = reactive({
  isDrawing: false,
  startX: 0, startY: 0,
  refBox: null,
  pixelPerMm: 0,
  refLength: 85.6
})

const compliance = reactive({
  status: null,
  message: ''
})

// =============================================
// 计算属性
// =============================================
const designTotal = computed(() => {
  return rebarConfig.value.reduce((sum, r) => sum + r.count, 0)
})

const avgDiameter = computed(() => {
  const preds = activeTab.value === 'column' ? columnResult.predictions : spacingResult.predictions
  const ppm = activeTab.value === 'column' ? columnCalibration.pixelPerMm : spacingCalibration.pixelPerMm
  if (!preds.length || !ppm) return '-'
  const diameters = preds.map(p => Math.min(p.width, p.height) / ppm)
  return (diameters.reduce((a, b) => a + b, 0) / diameters.length).toFixed(1)
})

// =============================================
// Tab 切换 —— 彻底状态隔离
// =============================================
const handleTabChange = () => {
  // 1. 清空图片（强制重新上传）
  imageFile.value = null
  imagePreview.value = null
  imgObj.value = null

  // 2. 清空 Tab 1 状态
  spacingResult.predictions = []
  spacingResult.detected_count = 0
  spacingResult.image_url = null
  spacingCalibration.isDrawing = false
  spacingCalibration.refBox = null
  spacingCalibration.pixelPerMm = 0
  spacingResults.value = []

  // 3. 清空 Tab 2 状态
  columnResult.predictions = []
  columnResult.detected_count = 0
  columnResult.hoop_path = []
  columnResult.inner_ties = []
  columnResult.image_url = null
  columnCalibration.isDrawing = false
  columnCalibration.refBox = null
  columnCalibration.pixelPerMm = 0
  compliance.status = null
  compliance.message = ''

  // 4. 清空 Canvas
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

// =============================================
// 共用：文件上传
// =============================================
const handleFileChange = (file) => {
  const rawFile = file.raw || file
  imageFile.value = rawFile

  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target.result
    imgObj.value = new Image()
    imgObj.value.onload = () => {
      // 仅重置当前 Tab 的检测结果（保留标定）
      if (activeTab.value === 'spacing') {
        spacingResult.predictions = []
        spacingResult.detected_count = 0
        spacingCalibration.refBox = null
        spacingCalibration.pixelPerMm = 0
        spacingResults.value = []
      } else {
        columnResult.predictions = []
        columnResult.detected_count = 0
        columnResult.hoop_path = []
        columnResult.inner_ties = []
        columnCalibration.refBox = null
        columnCalibration.pixelPerMm = 0
        compliance.status = null
        compliance.message = ''
      }
      nextTick(() => redrawCanvas())
    }
    imgObj.value.src = e.target.result
  }
  reader.readAsDataURL(rawFile)
}

// =============================================
// 共用：Canvas 标定（按 Tab 隔离标定状态）
// =============================================
const handleMouseDown = (e) => {
  if (!imgObj.value) return
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const mx = (e.clientX - rect.left) * scaleX
  const my = (e.clientY - rect.top) * scaleY

  const cal = activeTab.value === 'column' ? columnCalibration : spacingCalibration
  cal.isDrawing = true
  cal.startX = mx
  cal.startY = my
  cal.refBox = { x: mx, y: my, w: 0, h: 0 }
}

const handleMouseMove = (e) => {
  const cal = activeTab.value === 'column' ? columnCalibration : spacingCalibration
  if (!cal.isDrawing) return

  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const mx = (e.clientX - rect.left) * scaleX
  const my = (e.clientY - rect.top) * scaleY

  cal.refBox.w = mx - cal.startX
  cal.refBox.h = my - cal.startY
  redrawCanvas()
}

const handleMouseUp = () => {
  const cal = activeTab.value === 'column' ? columnCalibration : spacingCalibration
  if (cal.isDrawing && cal.refBox) {
    cal.isDrawing = false
    if (Math.abs(cal.refBox.w) > 5) {
      const pxW = Math.abs(cal.refBox.w)
      const refLen = activeTab.value === 'column' ? columnCalibration.refLength : spacingDetectParams.refLength
      cal.pixelPerMm = pxW / refLen
      ElMessage.success(`标定完成: ${cal.pixelPerMm.toFixed(3)} 像素/mm`)
    }
    redrawCanvas()
  }
}

// =============================================
// 开始检测（根据 Tab 调用不同接口）
// =============================================
const startAnalysis = async () => {
  if (!imageFile.value) {
    ElMessage.warning('请先上传图片')
    return
  }

  isLoading.value = true

  try {
    const formData = new FormData()
    formData.append('image', imageFile.value)

    if (activeTab.value === 'spacing') {
      // ---------- Tab 1: 间距检测 ----------
      spacingResults.value = []
      const extraParams = {}
      if (spacingCalibration.pixelPerMm > 0) {
        extraParams.component_type = componentType.value
        extraParams.pixel_per_mm = spacingCalibration.pixelPerMm
        extraParams.tolerance = spacingParams.tolerance
        if (componentType.value === 'slab_wall') {
          extraParams.target_spacing = spacingParams.designSpacing
        } else {
          extraParams.target_spacing_dense = spacingParams.denseSpacing
          extraParams.target_spacing_sparse = spacingParams.sparseSpacing
        }
      }

      const data = await api.analyze(formData, 'spacing', spacingDetectParams.confidence, spacingDetectParams.overlap, extraParams)
      spacingResult.predictions = data.predictions || []
      spacingResult.detected_count = spacingResult.predictions.length
      spacingResult.image_url = data.image_url

      if (data.spacings) {
        spacingResults.value = data.spacings
        const passed = data.spacings.filter(s => s.status !== 'fail').length
        ElMessage.success(`检测完成 | 间距 ${data.spacings.length} 段，合格 ${passed} 段`)
      } else {
        ElMessage.success(`检测完成，识别到 ${spacingResult.detected_count} 个目标`)
      }

    } else {
      // ---------- Tab 2: 柱截面检测 ----------
      const data = await api.analyze(formData, 'column', 40, 40)
      columnResult.predictions = data.predictions || []
      columnResult.detected_count = data.detected_count || columnResult.predictions.length
      columnResult.hoop_path = data.hoop_path || []
      columnResult.inner_ties = data.inner_ties || []
      columnResult.image_url = data.image_url

      if (designTotal.value > 0) {
        const compResult = await api.checkCompliance(columnResult.detected_count, designTotal.value)
        compliance.status = compResult.status
        compliance.message = compResult.message
      }

      ElMessage.success(`检测完成，识别到 ${columnResult.detected_count} 根纵筋`)
    }

    nextTick(() => redrawCanvas())

  } catch (error) {
    ElMessage.error('检测失败: ' + error.message)
  } finally {
    isLoading.value = false
  }
}

// =============================================
// Canvas 绘制（根据 Tab 绘制不同内容）
// =============================================
const redrawCanvas = () => {
  const canvas = canvasRef.value
  if (!canvas || !imgObj.value) return

  const ctx = canvas.getContext('2d')
  canvas.width = imgObj.value.width
  canvas.height = imgObj.value.height
  ctx.drawImage(imgObj.value, 0, 0)

  const cal = activeTab.value === 'column' ? columnCalibration : spacingCalibration
  const res = activeTab.value === 'column' ? columnResult : spacingResult

  // ---- 参照物框 ----
  if (cal.refBox && cal.refBox.w !== 0) {
    ctx.strokeStyle = '#ff9800'
    ctx.lineWidth = 3
    ctx.setLineDash([5, 5])
    ctx.strokeRect(cal.refBox.x, cal.refBox.y, cal.refBox.w, cal.refBox.h)
    ctx.setLineDash([])
    ctx.fillStyle = '#ff9800'
    ctx.font = '14px Arial'
    ctx.fillText('参照物', cal.refBox.x, cal.refBox.y - 5)
  }

  // ---- 检测框（两个Tab共用） ----
  ctx.strokeStyle = '#00e676'
  ctx.lineWidth = 2
  res.predictions.forEach((p, i) => {
    const x = p.x - p.width / 2
    const y = p.y - p.height / 2
    ctx.strokeRect(x, y, p.width, p.height)

    ctx.fillStyle = '#00e676'
    ctx.font = 'bold 12px Arial'
    ctx.fillText((i + 1).toString(), p.x - 4, p.y + 4)

    if (cal.pixelPerMm > 0) {
      const dia = (Math.min(p.width, p.height) / cal.pixelPerMm).toFixed(1)
      ctx.fillStyle = '#fff'
      ctx.font = '10px Arial'
      ctx.fillText(`φ${dia}`, x, y - 3)
    }
  })

  // ---- Tab 特有绘制 ----
  if (activeTab.value === 'spacing') {
    // 间距合规性线条
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
  } else {
    // 外箍筋凸包
    if (columnResult.hoop_path.length > 2) {
      ctx.strokeStyle = '#2196f3'
      ctx.lineWidth = 4
      ctx.setLineDash([])
      ctx.beginPath()
      ctx.moveTo(columnResult.hoop_path[0].x, columnResult.hoop_path[0].y)
      for (let i = 1; i < columnResult.hoop_path.length; i++) {
        ctx.lineTo(columnResult.hoop_path[i].x, columnResult.hoop_path[i].y)
      }
      ctx.closePath()
      ctx.stroke()

      columnResult.hoop_path.forEach(p => {
        ctx.fillStyle = '#2196f3'
        ctx.beginPath()
        ctx.arc(p.x, p.y, 6, 0, Math.PI * 2)
        ctx.fill()
      })
    }

    // 内拉筋
    columnResult.inner_ties.forEach(tie => {
      ctx.strokeStyle = '#ffeb3b'
      ctx.lineWidth = 2
      ctx.setLineDash([8, 4])
      ctx.beginPath()
      ctx.moveTo(tie.from.x, tie.from.y)
      ctx.lineTo(tie.to.x, tie.to.y)
      ctx.stroke()
    })
    ctx.setLineDash([])
  }
}

// =============================================
// 柱截面专用方法
// =============================================
const parsePingfa = (str) => {
  const results = []
  const regex = /(\d+)[CΦφ](\d+)/gi
  let match
  while ((match = regex.exec(str)) !== null) {
    results.push({ count: parseInt(match[1]), diameter: parseInt(match[2]) })
  }
  return results
}

const addRebar = () => {
  const value = rebarInput.value.trim().toUpperCase()
  const parsed = parsePingfa(value)
  if (parsed.length === 0) {
    ElMessage.warning('格式错误！请输入如 4C22 或 8C20')
    return
  }
  rebarConfig.value.push(...parsed)
  rebarInput.value = ''
}

const removeRebar = (index) => {
  rebarConfig.value.splice(index, 1)
}

const exportExcel = async () => {
  if (!columnResult.detected_count) {
    ElMessage.warning('请先进行检测')
    return
  }
  try {
    const blob = await api.exportExcel({
      column_id: columnInfo.columnId,
      section_size: [columnInfo.sectionWidth, columnInfo.sectionHeight],
      detected_count: columnResult.detected_count,
      design_total: designTotal.value,
      rebar_config: rebarConfig.value,
      compliance,
      predictions: columnResult.predictions
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `column_report_${Date.now()}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

// 保存记录（两个 Tab 复用）
const saveRecord = async () => {
  const res = activeTab.value === 'column' ? columnResult : spacingResult
  if (!res.detected_count) {
    ElMessage.warning('请先进行检测')
    return
  }

  try {
    const recordData = activeTab.value === 'column'
      ? {
          inspection_type: 'column',
          column_id: columnInfo.columnId,
          section_size: [columnInfo.sectionWidth, columnInfo.sectionHeight],
          detected_count: columnResult.detected_count,
          design_total: designTotal.value,
          rebar_config: rebarConfig.value,
          compliance,
          predictions: columnResult.predictions,
          hoop_path: columnResult.hoop_path,
          image_url: columnResult.image_url
        }
      : {
          inspection_type: 'spacing',
          detected_count: spacingResult.detected_count,
          predictions: spacingResult.predictions,
          image_url: spacingResult.image_url
        }

    await api.createRecord(recordData)
    ElMessage.success('记录已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}
</script>

<template>
  <el-container class="hidden-inspection-container">
    <!-- ============ 侧边栏 ============ -->
    <el-aside width="360px" class="sidebar">
      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" type="card" class="tab-switch" @tab-change="handleTabChange">
        <el-tab-pane label="间距与箍筋检测" name="spacing" />
        <el-tab-pane label="柱截面合规检测" name="column" />
      </el-tabs>

      <!-- ===== Tab 1: 间距参数区 ===== -->
      <template v-if="activeTab === 'spacing'">
        <!-- 构件类型 -->
        <el-card class="control-card">
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

          <div v-if="componentType === 'slab_wall'" class="spacing-inputs">
            <div class="param-item">
              <span>设计间距 (mm)</span>
              <el-input-number v-model="spacingParams.designSpacing" :min="10" :max="500" :step="10" />
            </div>
          </div>
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

        <!-- 检测参数 -->
        <el-card class="control-card">
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>检测参数</span>
            </div>
          </template>
          <div class="param-item">
            <span>置信度阈值</span>
            <el-slider v-model="spacingDetectParams.confidence" :min="10" :max="90" />
          </div>
          <div class="param-item">
            <span>参照物宽度 (mm)</span>
            <el-input-number v-model="spacingDetectParams.refLength" :min="1" :max="500" />
          </div>
        </el-card>
      </template>

      <!-- ===== Tab 2: 柱截面参数区 ===== -->
      <template v-if="activeTab === 'column'">
        <!-- 平法数据录入 -->
        <el-card class="control-card">
          <template #header>
            <div class="card-header">
              <el-icon><Edit /></el-icon>
              <span>平法数据录入</span>
            </div>
          </template>

          <el-form label-width="80px" size="small">
            <el-form-item label="柱号">
              <el-input v-model="columnInfo.columnId" placeholder="如 KZ1" />
            </el-form-item>
            <el-form-item label="截面尺寸">
              <div style="display: flex; gap: 8px; align-items: center;">
                <el-input-number v-model="columnInfo.sectionWidth" :min="100" :max="2000" />
                <span>×</span>
                <el-input-number v-model="columnInfo.sectionHeight" :min="100" :max="2000" />
                <span>mm</span>
              </div>
            </el-form-item>
          </el-form>

          <div class="rebar-input">
            <el-alert type="info" :closable="false" show-icon class="mb-3">
              输入格式：<code>4C22</code> 表示 4 根 φ22 钢筋
            </el-alert>
            <div style="display: flex; gap: 8px;">
              <el-input v-model="rebarInput" placeholder="如 4C22" @keyup.enter="addRebar" />
              <el-button type="primary" @click="addRebar">
                <el-icon><Plus /></el-icon>
              </el-button>
            </div>

            <div class="rebar-tags">
              <el-tag
                v-for="(r, i) in rebarConfig"
                :key="i"
                closable
                type="primary"
                @close="removeRebar(i)"
              >
                {{ r.count }}C{{ r.diameter }}
              </el-tag>
            </div>

            <div class="design-total">
              设计总根数：<span class="value">{{ designTotal }}</span>
            </div>
          </div>
        </el-card>

        <!-- 标定参数 -->
        <el-card class="control-card">
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>标定参数</span>
            </div>
          </template>
          <el-form label-width="80px" size="small">
            <el-form-item label="参照物宽">
              <el-input-number v-model="columnCalibration.refLength" :min="1" :max="500" /> mm
            </el-form-item>
          </el-form>
        </el-card>
      </template>

      <!-- ===== 共用：图片上传 ===== -->
      <el-card class="control-card">
        <template #header>
          <div class="card-header">
            <el-icon><Camera /></el-icon>
            <span>图像上传</span>
          </div>
        </template>

        <el-alert type="info" :closable="false" show-icon class="mb-3">
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

      <!-- ===== 共用：开始检测 ===== -->
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

      <!-- ===== Tab 1 结果 ===== -->
      <template v-if="activeTab === 'spacing' && spacingResult.detected_count">
        <el-card class="result-card result-pass">
          <template #header>
            <div class="card-header"><el-icon><DataAnalysis /></el-icon><span>检测结果</span></div>
          </template>
          <div class="result-stats">
            <div class="stat-item">
              <div class="stat-value">{{ spacingResult.detected_count }}</div>
              <div class="stat-label">检测数量</div>
            </div>
          </div>
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
      </template>

      <!-- ===== Tab 2 结果 ===== -->
      <template v-if="activeTab === 'column'">
        <!-- 合规判定 -->
        <el-card
          v-if="compliance.status"
          class="result-card"
          :class="{
            'result-pass': compliance.status === 'PASS',
            'result-fail': compliance.status === 'FAIL',
            'result-warning': compliance.status === 'WARNING'
          }"
        >
          <div class="compliance-result">
            <el-icon :size="48">
              <component :is="compliance.status === 'PASS' ? 'CircleCheck' : compliance.status === 'FAIL' ? 'CircleClose' : 'Warning'" />
            </el-icon>
            <div class="compliance-title">
              {{ compliance.status === 'PASS' ? '验收通过' : compliance.status === 'FAIL' ? '验收不通过' : '警告' }}
            </div>
            <div class="compliance-message">{{ compliance.message }}</div>
          </div>
        </el-card>

        <!-- 统计 -->
        <div class="stats-row" v-if="columnResult.detected_count">
          <div class="stat-card">
            <div class="stat-value" style="color:#63b3ed">{{ columnResult.detected_count }}</div>
            <div class="stat-label">检测数量</div>
          </div>
          <div class="stat-card">
            <div class="stat-value" style="color:#63b3ed">{{ avgDiameter }}</div>
            <div class="stat-label">平均直径</div>
          </div>
        </div>

        <!-- 导出 -->
        <div class="export-buttons" v-if="columnResult.detected_count">
          <el-button type="success" @click="exportExcel">
            <el-icon><Document /></el-icon> 导出 Excel
          </el-button>
          <el-button type="primary" @click="saveRecord">
            <el-icon><FolderAdd /></el-icon> 保存记录
          </el-button>
        </div>
      </template>
    </el-aside>

    <!-- ============ 主内容区 ============ -->
    <el-main class="main-content">
      <div class="canvas-header">
        <h2>
          {{ activeTab === 'spacing' ? '隐蔽验收 - 间距检测' : '柱截面合规检测' }}
          <el-tag :type="activeTab === 'spacing' ? '' : 'warning'" size="small">
            {{ activeTab === 'spacing' ? 'Side View' : 'Section View' }}
          </el-tag>
        </h2>
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

        <div v-if="!imgObj" class="canvas-placeholder">
          <el-icon :size="64"><Picture /></el-icon>
          <p>{{ activeTab === 'spacing' ? '请上传钢筋侧面图片' : '请上传柱截面图片' }}</p>
        </div>

        <!-- 图例 -->
        <div class="legend-box" v-if="(activeTab === 'spacing' && spacingResult.predictions.length) || (activeTab === 'column' && columnResult.predictions.length)">
          <template v-if="activeTab === 'spacing'">
            <div class="legend-item"><span class="dot" style="background:#00e676"></span>{{ spacingResults.length ? (componentType === 'beam_column' ? '非加密区合格' : '合格') : '检测框' }}</div>
            <div class="legend-item" v-if="spacingResults.length && componentType === 'beam_column'"><span class="dot" style="background:#00e5ff"></span>加密区合格</div>
            <div class="legend-item" v-if="spacingResults.length"><span class="dot" style="background:#ff1744"></span>不合格</div>
          </template>
          <template v-else>
            <div class="legend-item"><span class="dot" style="background:#00e676"></span>纵筋检测框</div>
            <div class="legend-item"><span class="dot" style="background:#2196f3"></span>外箍筋</div>
            <div class="legend-item"><span class="dot" style="background:#ffeb3b"></span>内拉筋</div>
          </template>
          <div class="legend-item"><span class="dot" style="background:#ff9800"></span>参照物</div>
        </div>
      </div>
    </el-main>
  </el-container>
</template>

<style scoped>
.hidden-inspection-container {
  height: 100vh;
  background: #1a1c2c;
}

.sidebar {
  background: #2d3748;
  padding: 16px;
  overflow-y: auto;
}

.tab-switch {
  margin-bottom: 16px;
}

.tab-switch :deep(.el-tabs__header) {
  margin: 0;
}

.tab-switch :deep(.el-tabs__item) {
  color: #a0aec0;
  font-size: 13px;
}

.tab-switch :deep(.el-tabs__item.is-active) {
  color: #409EFF;
  font-weight: 600;
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

.mode-radio {
  width: 100%;
}

.mode-radio :deep(.el-radio-button__inner) {
  width: 100%;
}

.spacing-inputs {
  margin-top: 12px;
}

.param-item {
  margin-bottom: 12px;
}

.param-item span {
  display: block;
  color: #a0aec0;
  font-size: 13px;
  margin-bottom: 6px;
}

.mb-3 {
  margin-bottom: 12px;
}

.rebar-tags {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.design-total {
  margin-top: 12px;
  color: #a0aec0;
  font-size: 13px;
}

.design-total .value {
  color: #63b3ed;
  font-weight: 700;
  font-size: 16px;
}

.rebar-input {
  margin-top: 4px;
}

.analyze-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  margin-bottom: 16px;
}

/* 结果卡片 */
.result-card {
  margin-bottom: 12px;
}

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

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #68d391;
}

.stat-label {
  font-size: 11px;
  color: #9ae6b4;
}

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

.save-btn {
  width: 100%;
  margin-top: 8px;
}

/* 柱截面合规 */
.compliance-result {
  text-align: center;
  padding: 12px 0;
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
  font-size: 12px;
  color: #a0aec0;
  margin-top: 4px;
}

.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.stat-card {
  flex: 1;
  background: #22252b;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-card .stat-label {
  color: #718096;
}

.export-buttons {
  display: flex;
  gap: 8px;
}

.export-buttons .el-button {
  flex: 1;
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
</style>

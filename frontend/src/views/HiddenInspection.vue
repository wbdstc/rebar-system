<script setup>
import { ref, reactive, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import api from '../api'

const router = useRouter()

// =============================================
// 全局共享状态
// =============================================

// =============================================
// 新手引导 (Tour) 状态
// =============================================
const tourOpen = ref(false)
const tourStep1Ref = ref(null)
const tourStep2Ref = ref(null)
const tourStep3Ref = ref(null)

import { onMounted } from 'vue'

onMounted(() => {
  const hasSeenTour = localStorage.getItem('hasSeenHiddenTour')
  if (!hasSeenTour) {
    setTimeout(() => {
      tourOpen.value = true
    }, 500)
  }
})

const onTourClose = () => {
  tourOpen.value = false
  localStorage.setItem('hasSeenHiddenTour', 'true')
}

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
  <el-container class="h-screen bg-slate-50 text-slate-800 relative flex flex-col overflow-hidden">
    <!-- 顶部导航栏 (工程蓝底色) -->
    <el-header class="relative z-20 flex justify-between items-center px-6 bg-blue-600 text-white shadow-md h-14 shrink-0">
      <div class="flex items-center gap-4">
        <el-button text class="!text-white hover:!bg-white/10" @click="router.push('/')">
          <el-icon class="mr-1 text-lg"><Back /></el-icon> 返回首页
        </el-button>
      </div>
      <div class="text-[17px] font-bold tracking-wider flex items-center gap-3">
        <span>工程智能验收系统</span>
        <div class="w-1.5 h-1.5 rounded-full bg-white/60"></div>
        <span class="text-blue-100 font-medium">隐蔽工程 AI 验收</span>
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
          <el-icon><Menu /></el-icon> 隐蔽验收模块
        </div>
        <el-menu
          :default-active="activeTab"
          class="!border-r-0 bg-transparent flex-1 pt-2 w-full custom-left-menu"
          @select="(i) => i === 'project' ? router.push('/records') : (activeTab = i)"
        >
          <el-menu-item index="project" class="menu-item-hover">
            <el-icon><List /></el-icon>
            <template #title>项目列表</template>
          </el-menu-item>
          
          <el-menu-item index="spacing" class="menu-item-hover">
            <el-icon><Grid /></el-icon>
            <template #title>间距与箍筋检测</template>
          </el-menu-item>
          
          <el-menu-item index="column" class="menu-item-hover">
            <el-icon><DataBoard /></el-icon>
            <template #title>柱截面合规检测</template>
          </el-menu-item>

          <el-menu-item index="settings" class="menu-item-hover" style="margin-top: auto; border-top: 1px solid rgba(255,255,255,0.1);">
            <el-icon><Setting /></el-icon>
            <template #title>个人设置</template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 新手引导 -->
      <el-tour v-model="tourOpen" @close="onTourClose">
        <el-tour-step :target="tourStep1Ref" title="第一步：配置参数" description="选择检测模式并配置对应的设计参数或平法图纸数据。" />
        <el-tour-step :target="tourStep2Ref" title="第二步：AI 配置" description="配置计算机视觉的检测严格程度及实物参照比例。" />
        <el-tour-step :target="tourStep3Ref" title="第三步：上传与计算" description="将现场图片拖拽至此，系统会自动生成验收合规报告并比对数据。" />
      </el-tour>

      <!-- 主工作区 -->
      <el-main class="bg-cad-grid p-6 flex flex-col gap-5 overflow-y-auto w-full">
        <!-- 顶部：参数配置卡片 -->
        <el-card ref="tourStep1Ref" class="dashboard-card shrink-0 shadow-sm border-slate-200 mb-5" :body-style="{ padding: '16px 24px' }">
          <div class="flex flex-col xl:flex-row gap-8 items-start xl:items-center">
            
            <!-- 平法/设计参数 (Left side) -->
            <div class="flex-1 xl:border-r border-slate-200 xl:pr-8 flex flex-col justify-center">
              
              <div class="flex items-center gap-6 mb-4">
                <div class="flex items-center gap-2 text-slate-800 font-bold text-base whitespace-nowrap">
                  <el-icon class="text-blue-500"><EditPen /></el-icon> 📝 检测参数与要求
                </div>
                <!-- 子模式切换器 -->
                <div class="flex-1">
                  <el-radio-group v-if="activeTab === 'spacing'" v-model="componentType" size="default">
                    <el-radio-button value="slab_wall">板/墙钢筋网</el-radio-button>
                    <el-radio-button value="beam_column">梁/柱箍筋</el-radio-button>
                  </el-radio-group>
                  <el-tag v-if="activeTab === 'column'" type="primary" effect="plain" class="border-blue-200">
                    柱截面隐蔽工程验收
                  </el-tag>
                </div>
              </div>

              <!-- 动态表单网格 -->
              <div class="bg-slate-50/50 border border-slate-100 rounded-xl p-4 w-full">
                <!-- Spacing 参数 -->
                <template v-if="activeTab === 'spacing'">
                  <div v-if="componentType === 'slab_wall'" class="grid grid-cols-1 md:grid-cols-2 gap-5 w-full">
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">设计间距 (mm)</span>
                      <el-input-number v-model="spacingParams.designSpacing" :min="10" :max="500" :step="10" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">误差阈值 (mm)</span>
                      <el-input-number v-model="spacingParams.tolerance" :min="1" :max="50" :step="5" class="!w-full" controls-position="right" />
                    </div>
                  </div>
                  <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-5 w-full">
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">加密区间距 (mm)</span>
                      <el-input-number v-model="spacingParams.denseSpacing" :min="10" :max="500" :step="10" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">非加密区间距 (mm)</span>
                      <el-input-number v-model="spacingParams.sparseSpacing" :min="10" :max="500" :step="10" class="!w-full" controls-position="right" />
                    </div>
                    <div class="flex flex-col gap-2">
                      <span class="text-slate-500 text-[13px] font-medium">误差阈值 (mm)</span>
                      <el-input-number v-model="spacingParams.tolerance" :min="1" :max="50" :step="5" class="!w-full" controls-position="right" />
                    </div>
                  </div>
                </template>

                <!-- Column 参数 -->
                <template v-if="activeTab === 'column'">
                  <div class="grid grid-cols-1 lg:grid-cols-2 gap-5 w-full">
                    <div class="flex flex-col gap-3">
                      <div class="flex items-center gap-3">
                        <span class="text-slate-500 text-[13px] font-medium w-20">柱号</span>
                        <el-input v-model="columnInfo.columnId" placeholder="如 KZ1" size="default" class="w-full" />
                      </div>
                      <div class="flex items-center gap-3">
                        <span class="text-slate-500 text-[13px] font-medium w-20">截面尺寸</span>
                        <div class="flex items-center gap-2 flex-1">
                          <el-input-number v-model="columnInfo.sectionWidth" :min="100" :max="2000" :step="50" class="!flex-1" controls-position="right" />
                          <span class="text-slate-400">×</span>
                          <el-input-number v-model="columnInfo.sectionHeight" :min="100" :max="2000" :step="50" class="!flex-1" controls-position="right" />
                          <span class="text-slate-400 text-xs">mm</span>
                        </div>
                      </div>
                    </div>
                    
                    <div class="flex flex-col gap-2">
                       <span class="text-slate-500 text-[13px] font-medium flex items-center justify-between">
                         平法配筋录入 (如 4C22)
                         <span class="text-slate-400 text-xs">设计总数: <span class="text-emerald-500 font-bold ml-1">{{ designTotal }}</span></span>
                       </span>
                       <div class="flex gap-2">
                         <el-input v-model="rebarInput" placeholder="输入配筋并回车" @keyup.enter="addRebar" size="default" class="flex-1" />
                         <el-button type="primary" @click="addRebar"><el-icon><Plus /></el-icon></el-button>
                       </div>
                       <div class="flex flex-wrap gap-2 mt-1 min-h-[30px]">
                         <el-tag v-for="(r, i) in rebarConfig" :key="i" closable type="primary" @close="removeRebar(i)" effect="plain">
                           {{ r.count }}C{{ r.diameter }}
                         </el-tag>
                       </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>

            <!-- AI Params (Right side) -->
            <div ref="tourStep2Ref" class="w-full xl:w-96 shrink-0 flex flex-col justify-center">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2 text-slate-800 font-bold text-base">
                  <el-icon class="text-indigo-500"><Setting /></el-icon> 🤖 AI 检测控制中心
                </div>
                <!-- 标定状态标识 -->
                <el-tag v-if="activeTab === 'spacing' ? spacingCalibration.pixelPerMm > 0 : columnCalibration.pixelPerMm > 0" type="success" effect="plain" size="small" class="border-green-200">
                  <el-icon class="mr-1"><Tools /></el-icon> 标定激活
                </el-tag>
              </div>

              <!-- Spacing 专属的滑动条 -->
              <div class="bg-indigo-50/50 p-4 rounded-xl border border-indigo-100 mb-3" v-if="activeTab === 'spacing'">
                <div class="flex justify-between items-center text-[13px] text-slate-600 mb-2">
                  <span class="font-medium">计算机视觉模型置信度阈值</span>
                  <span class="font-black text-indigo-600 text-lg tabular-nums leading-none"><span class="text-sm">≥</span> {{ spacingDetectParams.confidence }}<span class="text-xs font-normal text-indigo-400 ml-0.5">%</span></span>
                </div>
                <el-slider v-model="spacingDetectParams.confidence" :min="10" :max="90" class="custom-slider !mb-1" />
              </div>

              <!-- 两个Tab共用的参照物长度 -->
              <div class="flex flex-col gap-2 px-1">
                 <span class="text-slate-500 text-[13px] font-medium">现场参照物标定长度 (mm)</span>
                 <el-input-number v-if="activeTab === 'spacing'" v-model="spacingDetectParams.refLength" :min="1" :max="500" :step="0.1" class="!w-full" controls-position="right" />
                 <el-input-number v-if="activeTab === 'column'" v-model="columnCalibration.refLength" :min="1" :max="500" :step="0.1" class="!w-full" controls-position="right" />
              </div>

            </div>
          </div>
        </el-card>

        <!-- 底部：上传与比对卡片 -->
        <el-card class="dashboard-card flex-1 flex flex-col min-h-[400px] shadow-sm border-slate-200" :body-style="{ padding: '0', display: 'flex', flexDirection: 'column', height: '100%' }">
          
          <!-- 卡片头 -->
          <div class="px-5 py-3 border-b border-slate-100 flex justify-between items-center shrink-0 bg-white">
            <div class="text-slate-700 font-bold flex items-center gap-2">
              <el-icon class="text-blue-500"><Picture /></el-icon> 现场照片拍摄与验证
            </div>
            
            <div class="flex items-center gap-4">
               <el-tag v-if="activeTab === 'column' && compliance.status === 'PASS'" type="success" effect="dark" size="default" class="mr-2 px-4 border-0"><el-icon class="mr-1"><CircleCheckFilled /></el-icon> 验收通过</el-tag>
               <el-tag v-else-if="activeTab === 'column' && compliance.status === 'FAIL'" type="danger" effect="dark" size="default" class="mr-2 px-4 shadow-sm border-0"><el-icon class="mr-1"><Warning /></el-icon> {{ compliance.message }}</el-tag>
               <el-tag v-else-if="activeTab === 'column' && compliance.status === 'WARNING'" type="warning" effect="dark" size="default" class="mr-2 px-4 shadow-sm border-0"><el-icon class="mr-1"><Warning /></el-icon> {{ compliance.message }}</el-tag>
               <el-tag v-else-if="activeTab === 'spacing' && spacingResult.detected_count" type="success" effect="dark" size="default" class="mr-2 px-4 shadow-sm border-0"><el-icon class="mr-1"><CircleCheckFilled /></el-icon> 间距检测完成</el-tag>

               <el-button
                 type="primary"
                 :loading="isLoading"
                 loading-icon="Loading"
                 loading-text="云端计算中..."
                 :disabled="!imageFile"
                 class="px-8 shadow-md !text-sm font-bold tracking-wide"
                 style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); border: none;"
                 @click="startAnalysis"
               >
                 <el-icon class="mr-2"><Lightning /></el-icon>
                 开始合规检验
               </el-button>
            </div>
          </div>

          <!-- 画布内容 -->
          <div ref="tourStep3Ref" class="flex-1 relative bg-cad-grid overflow-hidden flex min-h-[400px]">
             <!-- Upload Full Overlay -->
             <div v-show="!imgObj" class="absolute inset-0 flex items-center justify-center pointer-events-none z-10 p-6">
                <el-upload
                  drag
                  :auto-upload="false"
                  :show-file-list="false"
                  accept="image/*"
                  @change="handleFileChange"
                  class="dashboard-upload w-full max-w-2xl h-full max-h-[400px] text-center flex items-center justify-center flex-col pointer-events-auto"
                >
                  <el-icon :size="48" class="text-blue-500/80 mb-4"><UploadFilled /></el-icon>
                  <p class="text-slate-700 font-medium text-lg">点击或拖拽上传隐蔽工程现场图片</p>
                  <p class="text-slate-500 text-sm mt-2">系统将自动运行 CV 大模型比对合规性，支持快捷键粘贴</p>
                </el-upload>
             </div>

             <!-- Canvas Area -->
             <div class="canvas-wrapper w-full h-full p-0 border-0 bg-transparent flex flex-col relative" :style="{ opacity: imgObj ? 1 : 0, pointerEvents: imgObj ? 'auto' : 'none' }">
                <div class="flex-1 w-full h-full relative overflow-hidden flex items-center justify-center bg-[#1e293b]">
                  <canvas ref="canvasRef" @mousedown="handleMouseDown" @mousemove="handleMouseMove" @mouseup="handleMouseUp" @mouseleave="handleMouseUp" class="max-w-full max-h-full cursor-crosshair shadow-2xl"></canvas>
                  
                  <!-- 比例尺提示 -->
                  <div class="absolute top-4 left-4 bg-black/60 backdrop-blur border border-white/20 px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-2" v-if="(activeTab === 'spacing' && spacingCalibration.pixelPerMm === 0) || (activeTab === 'column' && columnCalibration.pixelPerMm === 0)">
                    <span class="w-3 h-3 rounded-full bg-orange-500 animate-pulse"></span>
                    <span class="text-orange-300 text-xs font-medium">请在画面中框选已知宽度参照物</span>
                  </div>

                  <!-- Legend -->
                  <div class="absolute top-4 right-4 bg-black/60 backdrop-blur border border-white/20 p-3 rounded-xl shadow-lg flex flex-col gap-2" v-if="(activeTab === 'spacing' && spacingResult.predictions.length) || (activeTab === 'column' && columnResult.predictions.length)">
                    <template v-if="activeTab === 'spacing'">
                      <div class="flex items-center gap-2 text-xs text-white"><span class="w-3 h-3 rounded bg-[#00e676]"></span> {{ spacingResults.length ? (componentType === 'beam_column' ? '非加密区合格' : '合格') : '检测框' }}</div>
                      <div class="flex items-center gap-2 text-xs text-white" v-if="spacingResults.length && componentType === 'beam_column'"><span class="w-3 h-3 rounded bg-[#00e5ff]"></span>加密区合格</div>
                      <div class="flex items-center gap-2 text-xs text-white" v-if="spacingResults.length"><span class="w-3 h-3 rounded bg-[#ff1744]"></span>超限误差段</div>
                    </template>
                    <template v-else>
                      <div class="flex items-center gap-2 text-xs text-white"><span class="w-3 h-3 rounded bg-[#00e676]"></span> 纵轴检测框</div>
                      <div class="flex items-center gap-2 text-xs text-white"><span class="w-3 h-3 rounded bg-[#2196f3]"></span> 外层箍筋区域</div>
                      <div class="flex items-center gap-2 text-xs text-white"><span class="w-3 h-3 rounded bg-[#ffeb3b]"></span> 辅助内拉筋</div>
                    </template>
                    <div class="flex items-center gap-2 text-xs text-white"><span class="w-3 h-3 rounded bg-[#ff9800]"></span> 比例尺参照物</div>
                  </div>
                </div>
                
                <!-- Bottom Stat Bar -->
                <div v-if="(activeTab === 'spacing' && spacingResult.detected_count) || (activeTab === 'column' && columnResult.detected_count)" class="h-16 shrink-0 bg-white border-t border-slate-200 flex items-center justify-between px-6">
                  
                  <div class="flex items-center gap-6" v-if="activeTab === 'spacing'">
                    <div class="flex flex-col">
                      <span class="text-[11px] text-slate-500 uppercase tracking-wider font-bold">检测数量</span>
                      <span class="text-slate-800 font-black text-lg">{{ spacingResult.detected_count }}</span>
                    </div>
                    <div class="h-8 w-px bg-slate-200"></div>
                    <div class="flex flex-col">
                      <span class="text-[11px] text-slate-500 uppercase tracking-wider font-bold">间距段数</span>
                      <span class="text-slate-800 font-bold text-base">{{ spacingResults.length }}</span>
                    </div>
                    <div class="flex flex-col" v-if="spacingResults.length">
                      <span class="text-[11px] text-emerald-600 uppercase tracking-wider font-bold">合格</span>
                      <span class="text-emerald-500 font-bold text-base">{{ spacingResults.filter(s => s.status !== 'fail').length }}</span>
                    </div>
                    <div class="flex flex-col" v-if="spacingResults.length">
                      <span class="text-[11px] text-red-500 uppercase tracking-wider font-bold">不合格</span>
                      <span class="text-red-500 font-bold text-base">{{ spacingResults.filter(s => s.status === 'fail').length }}</span>
                    </div>
                  </div>

                  <div class="flex items-center gap-6" v-if="activeTab === 'column'">
                    <div class="flex flex-col">
                      <span class="text-[11px] text-slate-500 uppercase tracking-wider font-bold">实测主筋数</span>
                      <span class="text-slate-800 font-black text-lg">{{ columnResult.detected_count }}</span>
                    </div>
                     <div class="h-8 w-px bg-slate-200"></div>
                     <div class="flex flex-col">
                      <span class="text-[11px] text-slate-500 uppercase tracking-wider font-bold">预估平均直径</span>
                      <span class="text-slate-800 font-bold text-base">{{ avgDiameter }} <span class="text-xs font-normal">mm</span></span>
                    </div>
                  </div>

                  <div class="flex items-center gap-3">
                     <el-button v-if="activeTab === 'column'" @click="exportExcel" class="!px-6 shadow-sm"><el-icon class="mr-1"><Document /></el-icon> 导出报告</el-button>
                     <el-button type="success" @click="saveRecord" class="!px-6 font-bold shadow-md shadow-emerald-500/20"><el-icon class="mr-1"><FolderChecked /></el-icon> 提取入库</el-button>
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
  color: #bfdbfe !important;
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
  color: #2563eb !important;
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

/* 输入框 Hover / Focus 状态 */
:deep(.el-input-number:hover .el-input__wrapper),
:deep(.el-input:hover .el-input__wrapper) {
  box-shadow: 0 0 0 1px #93c5fd inset !important;
}

:deep(.el-input-number .el-input__wrapper.is-focus),
:deep(.el-input .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #3b82f6 inset !important;
  background-color: #ffffff !important;
}

/* 右侧对其覆盖 */
:deep(.el-input-number.is-controls-right .el-input__wrapper) {
  background-color: white !important;
}

.custom-slider :deep(.el-slider__bar) {
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
}

.custom-slider :deep(.el-slider__button) {
  border-color: #8b5cf6;
}

/* 大文件拖拽优化 */
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
  border: 2px dashed #93c5fd;
  padding: 0;
  width: 100%;
  height: 100%;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  background-color: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
}

.dashboard-upload.is-dragover :deep(.el-upload-dragger),
.dashboard-upload :deep(.el-upload-dragger:hover) {
  background-color: #eff6ff;
  border-color: #3b82f6;
  transform: scale(1.02);
}
</style>

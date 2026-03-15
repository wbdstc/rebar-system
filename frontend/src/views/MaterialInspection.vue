<script setup>
import { ref, reactive, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()

// =============================================
// 状态定义
// =============================================
const isLoading = ref(false)
const imageFile = ref(null)
const imagePreview = ref(null)
const canvasRef = ref(null)
const imgObj = ref(null)

// 进场原材参数
const materialParams = reactive({
  refLength: 85.6
})

// 通用检测参数
const detectParams = reactive({
  confidence: 40,
  overlap: 40
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

// =============================================
// 计算属性
// =============================================
const avgDiameter = computed(() => {
  if (!result.predictions.length || !calibration.pixelPerMm) return '-'
  const diameters = result.predictions.map(p =>
    Math.min(p.width, p.height) / calibration.pixelPerMm
  )
  return (diameters.reduce((a, b) => a + b, 0) / diameters.length).toFixed(1)
})

// =============================================
// 方法
// =============================================
const resetAll = () => {
  result.predictions = []
  result.detected_count = 0
  result.image_url = null
  calibration.refBox = null
  calibration.pixelPerMm = 0
  calibration.isDrawing = false
  imageFile.value = null
  imagePreview.value = null
  imgObj.value = null

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
      calibration.refBox = null
      calibration.pixelPerMm = 0
      nextTick(() => redrawCanvas())
    }
    imgObj.value.src = e.target.result
  }
  reader.readAsDataURL(rawFile)
}

// ---- Canvas 拖拽画框标定 ----
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
      calibration.pixelPerMm = pxW / materialParams.refLength
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

  try {
    const formData = new FormData()
    formData.append('image', imageFile.value)

    const data = await api.analyze(
      formData,
      'counting',
      detectParams.confidence,
      detectParams.overlap
    )

    result.predictions = data.predictions || []
    result.detected_count = result.predictions.length
    result.image_url = data.image_url

    ElMessage.success(`检测完成，识别到 ${result.detected_count} 根钢筋`)

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
}

// 保存记录
const saveRecord = async () => {
  if (!result.predictions.length) {
    ElMessage.warning('请先进行检测')
    return
  }

  try {
    await api.createRecord({
      inspection_type: 'material',
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
    <!-- 顶部导航栏 -->
    <el-header class="relative z-20 flex justify-between items-center px-6 bg-blue-600 text-white shadow-md h-14 shrink-0">
      <div class="flex items-center gap-4">
        <el-button text class="!text-white hover:!bg-white/10" @click="router.push('/')">
          <el-icon class="mr-1 text-lg"><Back /></el-icon> 返回首页
        </el-button>
      </div>
      <div class="text-[17px] font-bold tracking-wider flex items-center gap-3">
        <span>进场材料验收</span>
        <div class="w-1.5 h-1.5 rounded-full bg-white/60"></div>
        <span class="text-blue-100 font-medium">钢筋端面 AI 计数与直径测量</span>
      </div>
      <div class="flex items-center gap-4">
        <el-button text class="!text-white hover:!bg-white/10">
          <el-icon class="mr-1 text-lg"><QuestionFilled /></el-icon> 帮助
        </el-button>
      </div>
    </el-header>

    <el-container class="relative z-10 overflow-hidden flex-1">
      <!-- 左侧参数面板 -->
      <el-aside width="300px" class="bg-white border-r border-slate-200 shadow-sm flex flex-col z-20 overflow-y-auto">
        <div class="p-4 border-b border-slate-100 flex items-center gap-2 text-slate-800 text-sm font-bold">
          <el-icon class="text-blue-500"><Setting /></el-icon> 检测参数配置
        </div>

        <div class="p-4 flex flex-col gap-5">
          <!-- 参照物标定 -->
          <div class="flex flex-col gap-3">
            <div class="flex items-center gap-2 text-slate-700 font-bold text-sm">
              <el-icon class="text-orange-500"><Aim /></el-icon> 参照物标定
            </div>
            <div class="bg-orange-50/80 border border-orange-100 rounded-xl p-3">
              <span class="text-slate-500 text-[13px] font-medium block mb-2">参照物已知宽度 (mm)</span>
              <el-input-number v-model="materialParams.refLength" :min="1" :max="500" :step="0.1" :precision="1" class="!w-full" controls-position="right" />
              <div class="text-[12px] text-orange-500 flex items-center gap-1.5 mt-2">
                <el-icon><InfoFilled /></el-icon> 标准名片/卡牌通常为85.6mm宽
              </div>
            </div>
            <el-tag v-if="calibration.pixelPerMm > 0" type="success" effect="plain" size="small" class="border-green-200">
              <el-icon class="mr-1"><Tools /></el-icon> 标定 {{ calibration.pixelPerMm.toFixed(1) }}px/mm
            </el-tag>
          </div>

          <!-- AI 置信度 -->
          <div class="flex flex-col gap-3">
            <div class="flex items-center gap-2 text-slate-700 font-bold text-sm">
              <el-icon class="text-indigo-500"><Cpu /></el-icon> AI 检测参数
            </div>
            <div class="bg-indigo-50/50 p-3 rounded-xl border border-indigo-100">
              <div class="flex justify-between items-center text-[13px] text-slate-600 mb-2">
                <span class="font-medium">置信度阈值</span>
                <span class="font-black text-indigo-600 text-lg tabular-nums leading-none">≥ {{ detectParams.confidence }}<span class="text-xs font-normal text-indigo-400 ml-0.5">%</span></span>
              </div>
              <el-slider v-model="detectParams.confidence" :min="10" :max="90" class="custom-slider !mb-1" />
            </div>
          </div>

          <!-- 检测结果摘要 -->
          <div v-if="result.detected_count" class="flex flex-col gap-3">
            <div class="flex items-center gap-2 text-slate-700 font-bold text-sm">
              <el-icon class="text-emerald-500"><DataAnalysis /></el-icon> 检测结果
            </div>
            <div class="bg-emerald-50 border border-emerald-100 rounded-xl p-4">
              <div class="flex justify-between items-center text-sm mb-2">
                <span class="text-slate-500">检测数量</span>
                <span class="font-black text-emerald-600 text-2xl tabular-nums">{{ result.detected_count }}</span>
              </div>
              <div class="flex justify-between items-center text-sm">
                <span class="text-slate-500">平均直径</span>
                <span class="font-bold text-slate-800 tabular-nums">{{ avgDiameter }} mm</span>
              </div>
            </div>
            <el-button type="success" class="w-full font-bold shadow-md shadow-emerald-500/20" @click="saveRecord">
              <el-icon class="mr-1"><DocumentChecked /></el-icon> 提取并入库
            </el-button>
          </div>
        </div>
      </el-aside>

      <!-- 主工作区 -->
      <el-main class="bg-cad-grid p-0 flex flex-col overflow-hidden w-full">
        <!-- 顶部操作栏 -->
        <div class="px-5 py-3 border-b border-slate-100 flex justify-between items-center shrink-0 bg-white">
          <div class="text-slate-700 font-bold flex items-center gap-2">
            <el-icon class="text-blue-500"><Picture /></el-icon> 进场钢筋端面检测
          </div>
          <div class="flex items-center gap-4">
            <el-tag v-if="result.detected_count" type="success" effect="dark" size="default" class="mr-2 px-4 shadow-sm border-0">
              <el-icon class="mr-1"><CircleCheckFilled /></el-icon> 检测完成
            </el-tag>
            <el-button
              type="primary"
              :loading="isLoading"
              loading-text="AI 计数中..."
              :disabled="!imageFile"
              class="px-8 shadow-md !text-sm font-bold tracking-wide"
              style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); border: none;"
              @click="startAnalysis"
            >
              <el-icon class="mr-2"><Lightning /></el-icon>
              开始端面检测
            </el-button>
          </div>
        </div>

        <!-- 画布内容 -->
        <div class="flex-1 relative overflow-hidden flex min-h-[400px]" style="background-color: #eaeff5; background-image: radial-gradient(#d1d5db 1px, transparent 1px); background-size: 20px 20px;">
          <!-- Upload Overlay -->
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
                <div class="w-full h-full flex flex-col items-center justify-center py-16">
                  <div class="w-24 h-24 mb-6 rounded-full bg-blue-50 flex items-center justify-center shadow-inner border border-blue-100">
                    <el-icon :size="48" class="text-blue-500"><Camera /></el-icon>
                  </div>
                  <p class="text-slate-700 font-bold text-xl mb-2">上传进场钢筋端面照片</p>
                  <p class="text-slate-500 text-sm font-medium">拍摄钢筋断面截面，AI自动计数并估算直径</p>
                  <p class="text-orange-500 text-xs mt-3">💡 提示：框选已知参照物以获得精确的直径估算</p>
                </div>
              </el-upload>
            </div>
          </div>

          <!-- Canvas Area -->
          <div v-show="imgObj" class="absolute inset-0 w-full h-full flex items-center justify-center p-4 z-20 overflow-auto">
            <canvas
              ref="canvasRef"
              class="rounded shadow-xl bg-white max-w-full"
              style="cursor: crosshair; min-width: 400px; object-fit: contain;"
              @mousedown="handleMouseDown"
              @mousemove="handleMouseMove"
              @mouseup="handleMouseUp"
              @mouseleave="handleMouseUp"
            ></canvas>

            <!-- 重新上传按钮 -->
            <div class="absolute top-6 left-6 flex gap-2 z-30">
              <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" @change="handleFileChange">
                <el-button size="default" class="shadow-md bg-white text-slate-700 hover:text-blue-500 border-0">
                  <el-icon class="mr-1 font-bold text-lg"><RefreshRight /></el-icon> 重新上传
                </el-button>
              </el-upload>
            </div>

            <!-- 标定提示 -->
            <div class="absolute top-6 right-6 bg-black/60 backdrop-blur border border-white/20 px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-2" v-if="calibration.pixelPerMm === 0">
              <span class="w-3 h-3 rounded-full bg-orange-500 animate-pulse"></span>
              <span class="text-orange-300 text-xs font-medium">请在画面中框选已知宽度参照物</span>
            </div>

            <!-- 图例 -->
            <div class="absolute bottom-6 right-6 bg-white/95 backdrop-blur-md border border-slate-200 p-3 rounded-xl shadow-lg min-w-[160px] z-30" v-if="result.predictions.length">
              <div class="text-xs font-bold text-slate-800 border-b border-slate-100 pb-2 mb-2 tracking-widest uppercase">
                <el-icon class="mr-1 align-text-bottom"><InfoFilled /></el-icon> 图例
              </div>
              <div class="flex items-center gap-2 text-xs text-slate-600 mb-1.5 font-medium">
                <span class="w-3 h-3 rounded bg-[#00e676] shadow-sm"></span> 钢筋检测框
              </div>
              <div class="flex items-center gap-2 text-xs text-slate-600 font-medium">
                <span class="w-3 h-3 rounded bg-[#ff9800] border border-orange-400 shadow-sm border-dashed"></span> 参照物标定框
              </div>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
@reference "../style.css";

:deep(.el-input-number.is-controls-right .el-input__wrapper) {
  background-color: white !important;
}
</style>

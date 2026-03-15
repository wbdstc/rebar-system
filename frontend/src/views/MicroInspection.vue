<script setup>
import { ref, reactive } from 'vue'
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

// 原材微观核验结果
const materialResult = reactive({
  success: false,
  material_grade: '',
  is_seismic: false,
  diameter: 0,
  raw_text: ''
})

// =============================================
// 方法
// =============================================
const handleFileChange = (file) => {
  const rawFile = file.raw || file
  imageFile.value = rawFile

  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target.result
    // 重置结果
    materialResult.success = false
    materialResult.material_grade = ''
    materialResult.is_seismic = false
    materialResult.diameter = 0
    materialResult.raw_text = ''
  }
  reader.readAsDataURL(rawFile)
}

const startMaterialVerify = async () => {
  if (!imageFile.value) {
    ElMessage.warning('请先上传钢筋特写照片')
    return
  }

  isLoading.value = true
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
    isLoading.value = false
  }
}

const resetAll = () => {
  imageFile.value = null
  imagePreview.value = null
  materialResult.success = false
  materialResult.material_grade = ''
  materialResult.is_seismic = false
  materialResult.diameter = 0
  materialResult.raw_text = ''
}

// 保存记录
const saveRecord = async () => {
  if (!materialResult.success) {
    ElMessage.warning('请先进行检测')
    return
  }

  try {
    await api.createRecord({
      inspection_type: 'material_vlm',
      detected_count: 1,
      material_grade: materialResult.material_grade,
      is_seismic: materialResult.is_seismic,
      diameter: materialResult.diameter,
      raw_text: materialResult.raw_text
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
        <span>原材微观检测</span>
        <div class="w-1.5 h-1.5 rounded-full bg-white/60"></div>
        <span class="text-blue-100 font-medium">AI 钢筋轧印智能识别</span>
      </div>
      <div class="flex items-center gap-4">
        <el-button text class="!text-white hover:!bg-white/10">
          <el-icon class="mr-1 text-lg"><QuestionFilled /></el-icon> 帮助
        </el-button>
      </div>
    </el-header>

    <el-container class="relative z-10 overflow-hidden flex-1">
      <!-- 主内容区 -->
      <el-main class="p-0 flex flex-col overflow-hidden w-full h-full">
        <div class="flex-1 flex flex-col lg:flex-row overflow-hidden">

          <!-- 左侧：上传区 -->
          <div class="flex-1 flex flex-col overflow-hidden" style="background-color: #eaeff5; background-image: radial-gradient(#d1d5db 1px, transparent 1px); background-size: 20px 20px;">
            <!-- 操作栏 -->
            <div class="px-5 py-3 border-b border-slate-100 flex justify-between items-center shrink-0 bg-white">
              <div class="text-slate-700 font-bold flex items-center gap-2">
                <el-icon class="text-purple-500"><View /></el-icon> 钢筋轧印特写上传
              </div>
              <div class="flex items-center gap-3">
                <el-button v-if="imagePreview" text type="danger" @click="resetAll">
                  <el-icon class="mr-1"><Delete /></el-icon> 清除
                </el-button>
                <el-button
                  type="primary"
                  :loading="isLoading"
                  loading-text="VLM 大模型识别中..."
                  :disabled="!imageFile"
                  class="px-8 shadow-md !text-sm font-bold tracking-wide"
                  style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); border: none;"
                  @click="startMaterialVerify"
                >
                  <el-icon class="mr-2"><Cpu /></el-icon>
                  AI 轧印识别
                </el-button>
              </div>
            </div>

            <!-- 图片区 -->
            <div class="flex-1 relative overflow-hidden flex items-center justify-center p-6">
              <!-- 上传空状态 -->
              <div v-if="!imagePreview" class="w-full max-w-2xl h-full max-h-[500px]">
                <el-upload
                  drag
                  :auto-upload="false"
                  :show-file-list="false"
                  accept="image/*"
                  @change="handleFileChange"
                  class="dashboard-upload w-full h-full flex items-center justify-center flex-col bg-white/60 backdrop-blur-sm border-2 border-dashed border-purple-300 rounded-2xl shadow-sm hover:border-purple-500 hover:bg-white/80 transition-all"
                >
                  <div class="w-full h-full flex flex-col items-center justify-center py-16">
                    <div class="w-24 h-24 mb-6 rounded-full bg-purple-50 flex items-center justify-center shadow-inner border border-purple-100">
                      <el-icon :size="48" class="text-purple-500"><Camera /></el-icon>
                    </div>
                    <p class="text-slate-700 font-bold text-xl mb-2">上传钢筋轧印特写照片</p>
                    <p class="text-slate-500 text-sm font-medium mb-4">请拍摄钢筋表面轧印标识（如 4E 22）的高清特写</p>
                    <div class="text-purple-600 text-xs bg-purple-50 px-4 py-2 rounded-full border border-purple-100">
                      💡 AI 将自动识别牌号、抗震标记及公称直径
                    </div>
                  </div>
                </el-upload>
              </div>

              <!-- 已上传的图片预览 -->
              <div v-else class="relative max-w-full max-h-full">
                <img :src="imagePreview" class="max-h-[calc(100vh-200px)] max-w-full rounded-2xl shadow-2xl object-contain" />
                <!-- 重新上传 -->
                <div class="absolute top-4 left-4 z-30">
                  <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" @change="handleFileChange">
                    <el-button size="default" class="shadow-md bg-white text-slate-700 hover:text-purple-500 border-0">
                      <el-icon class="mr-1 font-bold text-lg"><RefreshRight /></el-icon> 重新上传
                    </el-button>
                  </el-upload>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧：结果面板 -->
          <div class="w-full lg:w-[400px] bg-white border-l border-slate-200 flex flex-col shrink-0 overflow-y-auto">
            <!-- 面板头 -->
            <div class="p-4 border-b border-slate-100 bg-slate-50 shrink-0">
              <div class="font-bold flex items-center gap-2 text-slate-800">
                <el-icon class="text-purple-500"><DataAnalysis /></el-icon> AI 微观识别结果
              </div>
            </div>

            <!-- 功能说明 -->
            <div class="p-4">
              <div class="text-sm text-purple-700 bg-purple-50 p-4 rounded-xl border border-purple-100 flex items-start gap-3 shadow-sm mb-4">
                <el-icon class="mt-0.5 text-xl"><Opportunity /></el-icon>
                <div class="leading-relaxed">
                  <strong class="text-purple-800 text-base">微观标牌语义识别</strong><br/>
                  <span class="text-purple-600/90">结合大语言与视觉大模型，自动锁定并提取钢筋端面轧制标识。无需手工录入参数，自动比对截面直径、牌号级别与抗震要求。</span>
                </div>
              </div>

              <!-- 识别结果卡片 -->
              <template v-if="materialResult.success">
                <div class="bg-gradient-to-br from-emerald-50 to-green-50 rounded-2xl border border-emerald-200 p-5 shadow-sm">
                  <div class="flex items-center gap-2 text-emerald-700 font-bold text-base mb-4">
                    <el-icon class="text-lg"><CircleCheckFilled /></el-icon> 识别成功
                  </div>

                  <div class="space-y-4">
                    <!-- 牌号 -->
                    <div class="flex justify-between items-center">
                      <span class="text-slate-500 text-sm">识别牌号</span>
                      <div class="text-emerald-700 font-black text-xl bg-emerald-100 px-4 py-1 rounded-lg">{{ materialResult.material_grade }}</div>
                    </div>

                    <!-- 抗震 -->
                    <div class="flex justify-between items-center">
                      <span class="text-slate-500 text-sm">带E抗震标识</span>
                      <el-tag :type="materialResult.is_seismic ? 'success' : 'warning'" effect="dark" size="default" class="border-0 font-bold">
                        {{ materialResult.is_seismic ? '✓ 满足抗震要求' : '✗ 未标注抗震' }}
                      </el-tag>
                    </div>

                    <!-- 直径 -->
                    <div class="flex justify-between items-center">
                      <span class="text-slate-500 text-sm">公称直径</span>
                      <div class="text-slate-800 font-bold text-lg">φ{{ materialResult.diameter }}<span class="text-sm font-normal text-slate-500 ml-1">mm</span></div>
                    </div>

                    <!-- 原始文本 -->
                    <div v-if="materialResult.raw_text" class="pt-3 border-t border-emerald-100">
                      <span class="text-slate-500 text-xs block mb-1">AI 原始识别文本</span>
                      <div class="text-slate-600 text-sm bg-white/80 p-2.5 rounded-lg font-mono">{{ materialResult.raw_text }}</div>
                    </div>
                  </div>
                </div>

                <!-- 入库按钮 -->
                <el-button type="success" class="w-full mt-4 font-bold shadow-md shadow-emerald-500/20" @click="saveRecord">
                  <el-icon class="mr-1"><DocumentChecked /></el-icon> 提取并入库
                </el-button>
              </template>

              <!-- 空状态 -->
              <div v-else-if="!isLoading" class="text-center text-slate-400 mt-12 flex flex-col gap-3 items-center">
                <el-icon :size="64" class="text-slate-200"><View /></el-icon>
                <div class="text-sm">上传轧印特写照片<br/>点击"AI 轧印识别"后<br/>在此展示识别结果</div>
              </div>

              <!-- 加载中 -->
              <div v-else class="text-center mt-12 flex flex-col gap-3 items-center">
                <el-icon :size="48" class="text-purple-400 animate-spin"><Loading /></el-icon>
                <div class="text-sm text-purple-600 font-medium">VLM 视觉大模型分析中...</div>
                <div class="text-xs text-slate-400">正在识别轧印标识，请稍候</div>
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
</style>

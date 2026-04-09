<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()

const isLoading = ref(false)
const imageFile = ref(null)
const imagePreview = ref(null)

const materialResult = reactive({
  success: false,
  material_grade: '',
  is_seismic: false,
  diameter: 0,
  raw_text: ''
})

const clearResult = () => {
  materialResult.success = false
  materialResult.material_grade = ''
  materialResult.is_seismic = false
  materialResult.diameter = 0
  materialResult.raw_text = ''
}

const hasImage = computed(() => Boolean(imagePreview.value))
const hasResult = computed(() => materialResult.success)

const stageStatus = computed(() => {
  if (hasResult.value) {
    return { label: '识别完成', type: 'success' }
  }

  if (hasImage.value) {
    return { label: '已上传', type: 'ready' }
  }

  return { label: '待上传', type: 'idle' }
})

const handleFileChange = (file) => {
  const rawFile = file?.raw || file
  if (!rawFile) return

  imageFile.value = rawFile

  const reader = new FileReader()
  reader.onload = (event) => {
    imagePreview.value = event.target?.result || null
    clearResult()
  }
  reader.readAsDataURL(rawFile)
}

const startMaterialVerify = async () => {
  if (!imageFile.value) {
    ElMessage.warning('请先上传钢筋轧印特写照片')
    return
  }

  isLoading.value = true
  clearResult()

  try {
    const formData = new FormData()
    formData.append('image', imageFile.value)

    const data = await api.verifyMaterial(formData)

    if (!data.success) {
      ElMessage.error(`识别失败: ${data.error || '未知错误'}`)
      return
    }

    materialResult.success = true
    materialResult.material_grade = data.material_grade || ''
    materialResult.is_seismic = Boolean(data.is_seismic)
    materialResult.diameter = data.diameter || 0
    materialResult.raw_text = data.raw_text || ''
    ElMessage.success('轧印识别成功')
  } catch (error) {
    ElMessage.error(`请求失败: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

const resetAll = () => {
  imageFile.value = null
  imagePreview.value = null
  clearResult()
}

const saveRecord = async () => {
  if (!materialResult.success) {
    ElMessage.warning('请先完成识别')
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
  } catch {
    ElMessage.error('保存失败')
  }
}
</script>

<template>
  <el-container class="inspection-container text-slate-800">
    <el-header class="micro-header">
      <div class="micro-header-side">
        <el-button text class="micro-header-btn" @click="router.push('/')">
          <el-icon class="mr-1 text-lg"><Back /></el-icon>
          返回首页
        </el-button>
      </div>

      <div class="micro-header-title">
        <span>原材微观检测</span>
        <span class="micro-header-divider"></span>
        <span class="micro-header-subtitle">AI 钢筋轧印识别</span>
      </div>

      <div class="micro-header-side micro-header-side-right">
        <el-button text class="micro-header-btn">
          <el-icon class="mr-1 text-lg"><QuestionFilled /></el-icon>
          帮助
        </el-button>
      </div>
    </el-header>

    <el-main class="micro-page">
      <section class="micro-shell">
        <section class="micro-card micro-stage-card">
          <div class="micro-toolbar">
            <div class="micro-toolbar-title">
              <div class="micro-section-label">
                <el-icon class="text-purple-500"><View /></el-icon>
                <span>钢筋轧印特写</span>
              </div>
              <div class="micro-stage-status" :class="`is-${stageStatus.type}`">
                <span class="micro-stage-status-dot"></span>
                <span>{{ stageStatus.label }}</span>
              </div>
            </div>

            <div class="micro-toolbar-actions">
              <el-button v-if="hasImage" text type="danger" @click="resetAll">
                <el-icon class="mr-1"><Delete /></el-icon>
                清除
              </el-button>

              <el-button
                type="primary"
                :loading="isLoading"
                loading-text="AI 识别中..."
                :disabled="!imageFile"
                class="micro-primary-btn"
                @click="startMaterialVerify"
              >
                <el-icon class="mr-2"><Cpu /></el-icon>
                AI 轧印识别
              </el-button>
            </div>
          </div>

          <div class="micro-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>上传清晰近拍，保证轧印居中</span>
          </div>

          <div class="micro-stage">
            <div v-if="!hasImage" class="micro-upload-wrap">
              <el-upload
                drag
                :auto-upload="false"
                :show-file-list="false"
                accept="image/*"
                @change="handleFileChange"
                class="dashboard-upload micro-upload"
              >
                <div class="micro-upload-inner">
                  <div class="micro-upload-icon">
                    <el-icon :size="48" class="text-purple-500"><Camera /></el-icon>
                  </div>
                  <p class="micro-upload-title">上传钢筋轧印特写</p>
                  <p class="micro-upload-description">示例：4E22、5E25 等清晰近景图像</p>
                </div>
              </el-upload>
            </div>

            <div v-else class="micro-preview-shell">
              <img :src="imagePreview" alt="钢筋轧印预览" class="micro-preview-image" />

              <div class="micro-floating-action">
                <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" @change="handleFileChange">
                  <el-button class="micro-float-btn">
                    <el-icon class="mr-1 text-lg"><RefreshRight /></el-icon>
                    重新上传
                  </el-button>
                </el-upload>
              </div>

              <div class="micro-preview-badge">{{ isLoading ? '识别中' : '待识别' }}</div>
            </div>
          </div>
        </section>

        <aside class="micro-card micro-result-card">
          <div class="micro-result-head">
            <div class="micro-section-label micro-section-label-dark">
              <el-icon class="text-purple-500"><DataAnalysis /></el-icon>
              <span>AI 识别结果</span>
            </div>
            <div class="micro-result-tags">
              <span>牌号</span>
              <span>抗震</span>
              <span>直径</span>
            </div>
          </div>

          <div class="micro-result-body">
            <template v-if="hasResult">
              <div class="micro-success-head">
                <div class="micro-success-title">
                  <el-icon class="text-lg"><CircleCheckFilled /></el-icon>
                  <span>识别成功</span>
                </div>
                <el-tag type="success" effect="dark" class="micro-success-tag">可入库</el-tag>
              </div>

              <div class="micro-stat-grid micro-stat-grid-compact">
                <div class="micro-stat-card micro-stat-card-primary">
                  <span class="micro-stat-label">识别牌号</span>
                  <strong class="micro-stat-value micro-stat-value-primary">{{ materialResult.material_grade }}</strong>
                </div>

                <div class="micro-stat-card">
                  <span class="micro-stat-label">抗震标识</span>
                  <strong class="micro-stat-value">{{ materialResult.is_seismic ? '满足要求' : '未标注' }}</strong>
                </div>

                <div class="micro-stat-card">
                  <span class="micro-stat-label">公称直径</span>
                  <strong class="micro-stat-value">φ{{ materialResult.diameter }}<span class="micro-stat-unit">mm</span></strong>
                </div>
              </div>

              <div class="micro-result-actions">
                <el-button type="success" class="micro-save-btn" @click="saveRecord">
                  <el-icon class="mr-1"><DocumentChecked /></el-icon>
                  提取并入库
                </el-button>
              </div>
            </template>

            <div v-else-if="!isLoading" class="micro-empty-state">
              <el-icon :size="64" class="micro-empty-icon"><PictureFilled /></el-icon>
              <h4>等待上传轧印特写</h4>
              <p>上传后点击“AI 轧印识别”</p>
            </div>

            <div v-else class="micro-empty-state">
              <el-icon :size="48" class="micro-loading-icon"><Loading /></el-icon>
              <h4>AI 正在识别</h4>
              <p>请稍候</p>
            </div>
          </div>
        </aside>
      </section>
    </el-main>
  </el-container>
</template>

<style scoped>
@reference "../style.css";

.inspection-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  background:
    radial-gradient(circle at 18% 0%, rgba(120, 174, 255, 0.12) 0%, transparent 34%),
    radial-gradient(circle at 82% 100%, rgba(110, 85, 255, 0.08) 0%, transparent 32%),
    linear-gradient(180deg, #e5eefb 0%, #edf3fc 28%, #f5f8ff 62%, #ffffff 100%);
  background-image: url('../assets/11.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.micro-header {
  position: relative;
  z-index: 20;
  height: 74px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 16px;
  padding: 0 22px;
  background: rgba(45, 108, 238, 0.82);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid rgba(147, 197, 253, 0.32);
  box-shadow: 0 12px 36px rgba(37, 99, 235, 0.18);
  color: #fff;
}

.micro-header-side {
  display: flex;
  align-items: center;
}

.micro-header-side-right {
  justify-content: flex-end;
}

.micro-header-btn {
  color: #fff !important;
  font-weight: 700;
}

.micro-header-btn:hover {
  background: rgba(255, 255, 255, 0.12) !important;
}

.micro-header-title {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 0 18px;
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0.02em;
  text-align: center;
}

.micro-header-divider {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.58);
  flex: none;
}

.micro-header-subtitle {
  color: rgba(219, 234, 254, 0.96);
  font-weight: 700;
}

.micro-page {
  flex: 1;
  padding: 16px 18px 18px;
}

.micro-shell {
  width: min(1320px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  align-items: stretch;
}

.micro-card {
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(145%);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
  overflow: hidden;
}

.micro-stage-card {
  display: flex;
  flex-direction: column;
}

.micro-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.55);
}

.micro-toolbar-title {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.micro-section-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #1f2937;
  font-size: 16px;
  font-weight: 800;
}

.micro-section-label-dark {
  font-size: 17px;
}

.micro-stage-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.micro-stage-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 4px currentColor;
  opacity: 0.28;
}

.micro-stage-status.is-idle {
  color: #64748b;
  background: rgba(148, 163, 184, 0.12);
}

.micro-stage-status.is-ready {
  color: #7c3aed;
  background: rgba(139, 92, 246, 0.12);
}

.micro-stage-status.is-success {
  color: #059669;
  background: rgba(16, 185, 129, 0.12);
}

.micro-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.micro-primary-btn {
  min-width: 156px;
  height: 40px;
  border: none;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.04em;
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%) !important;
  box-shadow: 0 14px 28px rgba(109, 40, 217, 0.24);
}

.micro-hint {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px 0;
  color: #6d28d9;
  font-size: 13px;
  font-weight: 600;
}

.micro-stage {
  min-height: 520px;
  padding: 16px 20px 20px;
  background-color: rgba(248, 250, 252, 0.52);
  background-image: radial-gradient(rgba(148, 163, 184, 0.45) 1px, transparent 1px);
  background-size: 24px 24px;
}

.micro-upload-wrap,
.micro-preview-shell,
.micro-upload {
  min-height: 100%;
}

.micro-upload-inner {
  min-height: 480px;
  padding: 28px 22px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.micro-upload-icon {
  width: 88px;
  height: 88px;
  margin-bottom: 18px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(243, 232, 255, 0.98));
  border: 1px solid rgba(221, 214, 254, 0.95);
  box-shadow: inset 0 2px 0 rgba(255, 255, 255, 0.85), 0 18px 36px rgba(139, 92, 246, 0.1);
}

.micro-upload-title {
  margin: 0;
  color: #0f172a;
  font-size: clamp(20px, 1.6vw, 26px);
  font-weight: 900;
}

.micro-upload-description {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
}

.micro-preview-shell {
  position: relative;
  min-height: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 18px 18px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.84) 0%, rgba(248, 250, 252, 0.96) 100%);
}

.micro-preview-image {
  max-width: 100%;
  max-height: 100%;
  border-radius: 20px;
  object-fit: contain;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.18);
}

.micro-floating-action {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 2;
}

.micro-float-btn {
  height: 38px;
  border: none;
  font-size: 13px;
  color: #334155;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.1);
}

.micro-preview-badge {
  position: absolute;
  right: 16px;
  bottom: 16px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
  color: #f8fafc;
  font-size: 11px;
  font-weight: 800;
}

.micro-result-card {
  display: flex;
  flex-direction: column;
}

.micro-result-head {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.78);
}

.micro-result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.micro-result-tags span {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(139, 92, 246, 0.08);
  border: 1px solid rgba(196, 181, 253, 0.6);
  color: #7c3aed;
  font-size: 11px;
  font-weight: 700;
}

.micro-result-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
}

.micro-success-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.micro-success-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #047857;
  font-size: 16px;
  font-weight: 900;
}

.micro-success-tag {
  border: none;
}

.micro-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.micro-stat-grid-compact {
  grid-template-columns: 1fr;
}

.micro-stat-card {
  min-height: 92px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(226, 232, 240, 0.88);
}

.micro-stat-card-primary {
  background: linear-gradient(135deg, #0f9f72 0%, #10b981 100%);
  border-color: transparent;
}

.micro-stat-card-primary .micro-stat-label,
.micro-stat-card-primary .micro-stat-value {
  color: #f0fdf4;
}

.micro-stat-label {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.micro-stat-value {
  color: #0f172a;
  font-size: 19px;
  font-weight: 900;
  line-height: 1.15;
}

.micro-stat-value-primary {
  font-size: 24px;
}

.micro-stat-unit {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.micro-result-actions {
  margin-top: auto;
}

.micro-save-btn {
  width: 100%;
  height: 42px;
  border: none;
  font-weight: 800;
  box-shadow: 0 14px 28px rgba(16, 185, 129, 0.2);
}

.micro-empty-state {
  flex: 1;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px 18px;
  border-radius: 20px;
  border: 1px dashed rgba(196, 181, 253, 0.8);
  background: rgba(255, 255, 255, 0.72);
}

.micro-empty-icon {
  color: #c4b5fd;
}

.micro-loading-icon {
  color: #8b5cf6;
  animation: spin 1s linear infinite;
}

.micro-empty-state h4 {
  margin: 14px 0 6px;
  color: #1e293b;
  font-size: 16px;
  font-weight: 900;
}

.micro-empty-state p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.65;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1180px) {
  .micro-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .micro-header {
    height: auto;
    grid-template-columns: 1fr;
    justify-items: start;
    padding: 14px 16px;
  }

  .micro-header-title {
    padding: 0;
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: 10px;
    text-align: left;
  }

  .micro-header-side-right {
    justify-content: flex-start;
  }

  .micro-page {
    padding: 12px;
  }

  .micro-shell {
    gap: 12px;
  }

  .micro-card {
    border-radius: 22px;
  }

  .micro-toolbar,
  .micro-result-head,
  .micro-result-body,
  .micro-stage {
    padding-left: 16px;
    padding-right: 16px;
  }

  .micro-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .micro-upload-inner,
  .micro-preview-shell {
    min-height: 380px;
  }

  .micro-floating-action {
    left: 16px;
    right: 16px;
  }

  .micro-floating-action :deep(.el-upload) {
    width: 100%;
  }

  .micro-float-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>

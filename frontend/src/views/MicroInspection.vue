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
    return {
      label: '识别完成',
      className: 'is-success'
    }
  }

  if (hasImage.value) {
    return {
      label: '图像已就绪',
      className: 'is-ready'
    }
  }

  return {
    label: '等待上传',
    className: 'is-idle'
  }
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
        <span class="micro-header-subtitle">AI 钢筋轧印智能识别</span>
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
        <div class="micro-main">
          <div class="micro-layout">
            <section class="micro-stage-panel">
              <div class="micro-toolbar">
                <div class="micro-toolbar-title">
                  <div class="micro-section-label">
                    <el-icon class="text-purple-500"><View /></el-icon>
                    <span>钢筋轧印特写上传</span>
                  </div>
                  <div class="micro-stage-status" :class="stageStatus.className">
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

              <div class="micro-stage-intro">
                <div class="micro-stage-copy">
                  <p class="micro-stage-eyebrow">更聚焦的特写，更稳定的识别结果</p>
                  <h3>把页面重心放回图像本身，让识别流程更从容</h3>
                  <p class="micro-stage-description">
                    建议画面保留 1 至 2 根钢筋，轧印区域尽量居中，减少强反光与透视变形。上传后可直接复用右侧结果完成入库。
                  </p>
                </div>

                <div class="micro-stage-tips">
                  <span>高清近拍</span>
                  <span>轧印居中</span>
                  <span>减少反光</span>
                </div>
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
                        <el-icon :size="52" class="text-purple-500"><Camera /></el-icon>
                      </div>
                      <p class="micro-upload-title">上传钢筋轧印特写照片</p>
                      <p class="micro-upload-description">
                        请拍摄钢筋表面轧印标识，如 4E22、5E25 等清晰近景图像
                      </p>
                      <div class="micro-upload-tags">
                        <span>自动识别牌号</span>
                        <span>自动识别抗震标记</span>
                        <span>自动提取公称直径</span>
                      </div>
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

                  <div class="micro-preview-caption">
                    <div>
                      <div class="micro-preview-caption-label">当前图像</div>
                      <div class="micro-preview-caption-title">已载入轧印特写，可直接启动 AI 识别</div>
                    </div>
                    <div class="micro-preview-caption-badge">{{ isLoading ? '识别中' : '待识别' }}</div>
                  </div>
                </div>
              </div>
            </section>

            <aside class="micro-results">
              <div class="micro-results-head">
                <div class="micro-section-label micro-section-label-dark">
                  <el-icon class="text-purple-500"><DataAnalysis /></el-icon>
                  <span>AI 微观识别结果</span>
                </div>
                <p>
                  结合视觉模型与语义规则，自动解析钢筋轧印中的牌号、抗震标记与公称直径，减少人工录入和判断成本。
                </p>
              </div>

              <div class="micro-results-body">
                <div class="micro-info-card">
                  <div class="micro-info-icon">
                    <el-icon><Opportunity /></el-icon>
                  </div>
                  <div class="micro-info-content">
                    <strong>微观标牌语义识别</strong>
                    <span>系统会优先锁定轧印区域，再结合行业规则输出可直接入库的结构化结果。</span>
                  </div>
                </div>

                <template v-if="hasResult">
                  <div class="micro-success-card">
                    <div class="micro-success-head">
                      <div class="micro-success-title">
                        <el-icon class="text-lg"><CircleCheckFilled /></el-icon>
                        <span>识别成功</span>
                      </div>
                      <el-tag type="success" effect="dark" class="micro-success-tag">结果可信</el-tag>
                    </div>

                    <div class="micro-stat-grid">
                      <div class="micro-stat-card micro-stat-card-primary">
                        <span class="micro-stat-label">识别牌号</span>
                        <strong class="micro-stat-value micro-stat-value-primary">{{ materialResult.material_grade }}</strong>
                      </div>

                      <div class="micro-stat-card">
                        <span class="micro-stat-label">抗震标识</span>
                        <strong class="micro-stat-value">{{ materialResult.is_seismic ? '满足要求' : '未标注' }}</strong>
                        <span class="micro-stat-note">{{ materialResult.is_seismic ? '检测到 E 标识' : '未检测到 E 标识' }}</span>
                      </div>

                      <div class="micro-stat-card">
                        <span class="micro-stat-label">公称直径</span>
                        <strong class="micro-stat-value">φ{{ materialResult.diameter }}<span class="micro-stat-unit">mm</span></strong>
                        <span class="micro-stat-note">可直接用于现场核验</span>
                      </div>

                      <div class="micro-stat-card">
                        <span class="micro-stat-label">建议动作</span>
                        <strong class="micro-stat-value">提取入库</strong>
                        <span class="micro-stat-note">保存到检测记录中心</span>
                      </div>
                    </div>

                    <div v-if="materialResult.raw_text" class="micro-raw-card">
                      <span class="micro-stat-label">AI 原始识别文本</span>
                      <div class="micro-raw-text">{{ materialResult.raw_text }}</div>
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
                  <el-icon :size="66" class="micro-empty-icon"><PictureFilled /></el-icon>
                  <h4>结果区正在等待一张清晰的轧印特写</h4>
                  <p>上传后点击“AI 轧印识别”，右侧会自动生成结构化结果与入库动作。</p>
                  <div class="micro-empty-grid">
                    <div class="micro-empty-item">
                      <span>01</span>
                      <strong>上传特写</strong>
                    </div>
                    <div class="micro-empty-item">
                      <span>02</span>
                      <strong>AI 解析</strong>
                    </div>
                    <div class="micro-empty-item">
                      <span>03</span>
                      <strong>提取入库</strong>
                    </div>
                  </div>
                </div>

                <div v-else class="micro-loading-state">
                  <el-icon :size="50" class="micro-loading-icon"><Loading /></el-icon>
                  <h4>AI 正在识别轧印信息</h4>
                  <p>系统正在分析牌号、抗震标记与公称直径，请稍候片刻。</p>
                </div>
              </div>
            </aside>
          </div>
        </div>
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
  overflow: hidden;
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
  min-height: 0;
  padding: 14px 18px 16px;
  overflow: hidden;
}

.micro-shell {
  width: min(1380px, 100%);
  height: 100%;
  min-height: 0;
  margin: 0 auto;
}

.micro-main {
  height: 100%;
  min-height: 0;
  border-radius: 30px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(22px) saturate(140%);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
}

.micro-layout {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.14fr) minmax(360px, 410px);
}

.micro-stage-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 12% 14%, rgba(139, 92, 246, 0.06) 0%, transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.44) 0%, rgba(248, 250, 252, 0.72) 100%);
}

.micro-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 20px 14px;
  background: rgba(255, 255, 255, 0.44);
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
  letter-spacing: 0.04em;
}

.micro-stage-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 4px currentColor;
  opacity: 0.35;
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

.micro-stage-intro {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 20px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.55);
}

.micro-stage-copy {
  max-width: 620px;
}

.micro-stage-eyebrow {
  margin: 0 0 4px;
  color: #7c3aed;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.micro-stage-copy h3 {
  margin: 0;
  color: #0f172a;
  max-width: 560px;
  font-size: clamp(18px, 1.35vw, 24px);
  font-weight: 900;
  line-height: 1.2;
}

.micro-stage-description {
  margin: 8px 0 0;
  max-width: 560px;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.micro-stage-tips {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 8px;
}

.micro-stage-tips span {
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(196, 181, 253, 0.72);
  color: #6d28d9;
  font-size: 11px;
  font-weight: 700;
  box-shadow: 0 6px 16px rgba(124, 58, 237, 0.08);
}

.micro-stage {
  flex: 1;
  min-height: 0;
  padding: 16px 20px 18px;
  display: flex;
  align-items: stretch;
  justify-content: center;
  overflow: hidden;
  background-color: rgba(248, 250, 252, 0.52);
  background-image: radial-gradient(rgba(148, 163, 184, 0.45) 1px, transparent 1px);
  background-size: 24px 24px;
}

.micro-upload-wrap,
.micro-preview-shell {
  width: min(100%, 900px);
  height: 100%;
  min-height: 0;
}

.micro-upload {
  height: 100%;
}

.micro-upload-inner {
  height: 100%;
  min-height: 340px;
  padding: 28px 22px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.micro-upload-icon {
  width: 90px;
  height: 90px;
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
  font-size: clamp(18px, 1.4vw, 24px);
  font-weight: 900;
}

.micro-upload-description {
  max-width: 560px;
  margin: 10px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
}

.micro-upload-tags {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.micro-upload-tags span {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(196, 181, 253, 0.72);
  color: #7c3aed;
  font-size: 11px;
  font-weight: 700;
}

.micro-preview-shell {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 18px 68px;
  border-radius: 30px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84) 0%, rgba(248, 250, 252, 0.96) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 24px 48px rgba(15, 23, 42, 0.06);
}

.micro-preview-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top right, rgba(192, 132, 252, 0.12) 0%, transparent 28%),
    radial-gradient(circle at bottom left, rgba(96, 165, 250, 0.08) 0%, transparent 28%);
  pointer-events: none;
}

.micro-preview-image {
  position: relative;
  z-index: 1;
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

.micro-preview-caption {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 16px;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(16px);
  color: #f8fafc;
}

.micro-preview-caption-label {
  margin-bottom: 2px;
  color: rgba(191, 219, 254, 0.88);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.micro-preview-caption-title {
  font-size: 13px;
  font-weight: 700;
}

.micro-preview-caption-badge {
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(167, 139, 250, 0.18);
  color: #ddd6fe;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.micro-results {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.74) 0%, rgba(248, 250, 252, 0.92) 100%);
  border-left: 1px solid rgba(255, 255, 255, 0.58);
}

.micro-results-head {
  padding: 16px 18px 14px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.78);
}

.micro-results-head p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}

.micro-results-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  overflow-y: auto;
}

.micro-info-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(245, 243, 255, 0.98) 0%, rgba(250, 245, 255, 0.88) 100%);
  border: 1px solid rgba(221, 214, 254, 0.9);
  box-shadow: 0 10px 24px rgba(124, 58, 237, 0.06);
}

.micro-info-icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(139, 92, 246, 0.12);
  color: #7c3aed;
  flex: none;
}

.micro-info-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.micro-info-content strong {
  color: #581c87;
  font-size: 14px;
}

.micro-info-content span {
  color: #7e22ce;
  font-size: 12px;
  line-height: 1.65;
}

.micro-success-card {
  padding: 16px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(236, 253, 245, 0.98) 0%, rgba(240, 253, 244, 0.88) 100%);
  border: 1px solid rgba(167, 243, 208, 0.9);
  box-shadow: 0 14px 30px rgba(16, 185, 129, 0.08);
}

.micro-success-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
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

.micro-stat-card {
  min-height: 96px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(220, 252, 231, 0.88);
}

.micro-stat-card-primary {
  background: linear-gradient(135deg, #0f9f72 0%, #10b981 100%);
  border-color: transparent;
}

.micro-stat-card-primary .micro-stat-label,
.micro-stat-card-primary .micro-stat-value,
.micro-stat-card-primary .micro-stat-note {
  color: #f0fdf4;
}

.micro-stat-label {
  color: #64748b;
  font-size: 12px;
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

.micro-stat-note {
  color: #64748b;
  font-size: 11px;
  line-height: 1.5;
}

.micro-stat-unit {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.micro-raw-card {
  margin-top: 10px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(220, 252, 231, 0.9);
}

.micro-raw-text {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  color: #334155;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 12px;
  line-height: 1.55;
  word-break: break-all;
}

.micro-result-actions {
  margin-top: 2px;
}

.micro-save-btn {
  width: 100%;
  height: 42px;
  border: none;
  font-weight: 800;
  box-shadow: 0 14px 28px rgba(16, 185, 129, 0.2);
}

.micro-empty-state,
.micro-loading-state {
  flex: 1;
  min-height: 240px;
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

.micro-empty-state h4,
.micro-loading-state h4 {
  margin: 14px 0 6px;
  color: #1e293b;
  font-size: 16px;
  font-weight: 900;
}

.micro-empty-state p,
.micro-loading-state p {
  margin: 0;
  max-width: 280px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.65;
}

.micro-empty-grid {
  width: 100%;
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.micro-empty-item {
  padding: 10px 8px;
  border-radius: 14px;
  background: rgba(245, 243, 255, 0.9);
  border: 1px solid rgba(221, 214, 254, 0.8);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.micro-empty-item span {
  color: #a78bfa;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.1em;
}

.micro-empty-item strong {
  color: #5b21b6;
  font-size: 13px;
  font-weight: 800;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1360px) {
  .micro-layout {
    grid-template-columns: minmax(0, 1fr) 380px;
  }

  .micro-stage-copy h3 {
    font-size: 22px;
  }
}

@media (max-width: 1180px) {
  .micro-page {
    padding: 16px;
    overflow: auto;
  }

  .micro-shell,
  .micro-main,
  .micro-layout {
    height: auto;
    min-height: auto;
  }

  .micro-layout {
    grid-template-columns: 1fr;
  }

  .micro-results {
    border-left: none;
    border-top: 1px solid rgba(226, 232, 240, 0.72);
  }

  .micro-stage {
    overflow: visible;
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

  .micro-main {
    border-radius: 22px;
  }

  .micro-toolbar,
  .micro-stage-intro,
  .micro-stage,
  .micro-results-head,
  .micro-results-body {
    padding-left: 16px;
    padding-right: 16px;
  }

  .micro-toolbar,
  .micro-stage-intro,
  .micro-preview-caption {
    flex-direction: column;
    align-items: flex-start;
  }

  .micro-stage {
    min-height: 460px;
    padding-bottom: 18px;
  }

  .micro-stage-tips {
    justify-content: flex-start;
  }

  .micro-upload-inner {
    min-height: 420px;
    padding: 32px 18px;
  }

  .micro-upload-title {
    font-size: 24px;
  }

  .micro-preview-shell {
    min-height: 420px;
    padding: 78px 16px 100px;
    border-radius: 22px;
  }

  .micro-floating-action {
    top: 16px;
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

  .micro-preview-caption {
    left: 16px;
    right: 16px;
    bottom: 16px;
  }

  .micro-stat-grid,
  .micro-empty-grid {
    grid-template-columns: 1fr;
  }
}
</style>

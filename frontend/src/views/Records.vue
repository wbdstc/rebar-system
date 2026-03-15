<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const router = useRouter()

const loading = ref(false)
const records = ref([])
const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})
const filterType = ref('')

// 类型映射
const typeMap = {
  spacing: { label: '间距检测', type: 'primary' },
  counting: { label: '计数检测', type: 'success' },
  column: { label: '柱截面检测', type: 'warning' },
  material: { label: '端面验收', type: '' },
  material_vlm: { label: '微观识别', type: 'danger' }
}

// 状态映射
const statusMap = {
  PASS: { label: '通过', type: 'success' },
  FAIL: { label: '不通过', type: 'danger' },
  WARNING: { label: '警告', type: 'warning' }
}

// 加载数据
const loadRecords = async () => {
  loading.value = true
  try {
    const data = await api.getRecords(
      pagination.value.current,
      pagination.value.pageSize,
      filterType.value || null
    )
    records.value = data.records
    pagination.value.total = data.total
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 分页变化
const handlePageChange = (page) => {
  pagination.value.current = page
  loadRecords()
}

// 筛选变化
const handleFilterChange = () => {
  pagination.value.current = 1
  loadRecords()
}

// 删除记录
const handleDelete = async (record) => {
  try {
    await ElMessageBox.confirm('确定要删除该检测记录吗？', '确认删除', {
      type: 'warning'
    })
    await api.deleteRecord(record.id)
    ElMessage.success('删除成功')
    loadRecords()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 导出 Excel
const handleExport = async (record) => {
  try {
    const blob = await api.exportExcel({
      column_id: record.column_id,
      section_size: record.section_size,
      detected_count: record.detected_count,
      design_total: record.design_total,
      rebar_config: record.rebar_config,
      compliance: {
        status: record.compliance_status,
        message: record.compliance_message
      }
    })
    
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${record.record_id}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

// 格式化时间
const formatTime = (isoString) => {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadRecords()
})
</script>

<template>
  <el-container class="flex flex-col h-screen bg-records bg-cover bg-center bg-no-repeat bg-fixed text-slate-800 relative">
    <div class="absolute inset-0 bg-white/40 backdrop-blur-sm pointer-events-none"></div>

    <el-header class="page-header bg-white/70 backdrop-blur-2xl border-b border-white/60 shadow-sm relative z-10">
      <div class="header-left flex items-center gap-3">
        <el-button text @click="router.push('/')">
          <el-icon><Back /></el-icon>
        </el-button>
        <h2 class="text-slate-800 font-bold m-0">检测数据中心</h2>
      </div>
      <div class="header-right flex gap-3">
        <el-select v-model="filterType" placeholder="全部类型" clearable @change="handleFilterChange">
          <el-option value="spacing" label="间距检测" />
          <el-option value="counting" label="计数检测" />
          <el-option value="column" label="柱截面检测" />
        </el-select>
        <el-button type="primary" @click="loadRecords">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </el-header>

    <el-main class="p-6 relative z-10">
      <el-table :data="records" v-loading="loading" stripe style="width: 100%" class="custom-table">
        <el-table-column prop="record_id" label="记录编号" width="180" />
        <el-table-column prop="inspection_type" label="检测类型" width="120">
          <template #default="{ row }">
            <el-tag :type="typeMap[row.inspection_type]?.type || 'info'" size="small">
              {{ typeMap[row.inspection_type]?.label || row.inspection_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="column_id" label="柱号" width="100" />
        <el-table-column prop="detected_count" label="检测数量" width="100" align="center" />
        <el-table-column prop="design_total" label="设计数量" width="100" align="center" />
        <el-table-column prop="compliance_status" label="合规状态" width="100">
          <template #default="{ row }">
            <el-tag 
              v-if="row.compliance_status" 
              :type="statusMap[row.compliance_status]?.type || 'info'" 
              size="small"
            >
              {{ statusMap[row.compliance_status]?.label || row.compliance_status }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="project_name" label="项目名称" min-width="150" />
        <el-table-column prop="inspector" label="检测人员" width="100" />
        <el-table-column prop="created_at" label="检测时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click="handleExport(row)">
              <el-icon><Download /></el-icon>
            </el-button>
            <el-button type="danger" size="small" text @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.current"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>

      <!-- 空状态 -->
      <el-empty v-if="!loading && records.length === 0" description="暂无检测记录" />
    </el-main>
  </el-container>
</template>

<style scoped>
@reference "../style.css";

.bg-records {
  background-image: url('../assets/11.jpg');
}

.page-header {
  @apply flex justify-between items-center px-6;
}

.custom-table {
  @apply bg-white/60 backdrop-blur-xl border border-white/60 rounded-xl overflow-hidden shadow-md;
  --el-table-border-color: rgba(255, 255, 255, 0.5);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.4);
}

.custom-table :deep(th.el-table__cell) {
  @apply !bg-white/40 !text-slate-800 font-semibold !border-b !border-white/50;
}

.custom-table :deep(td.el-table__cell) {
  @apply bg-transparent text-slate-700 border-b border-white/30;
}

.custom-table :deep(.el-table__row--striped td.el-table__cell) {
  @apply bg-white/30;
}

/* 隐藏外边框 */
.custom-table::before, .custom-table::after {
  display: none;
}

.text-muted {
  color: #718096;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>

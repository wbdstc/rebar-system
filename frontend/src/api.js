import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
    timeout: 60000,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 请求拦截器
api.interceptors.request.use(
    config => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
        return config
    },
    error => {
        return Promise.reject(error)
    }
)

// 响应拦截器
api.interceptors.response.use(
    response => {
        return response.data
    },
    error => {
        console.error('[API Error]', error.message)
        return Promise.reject(error)
    }
)

// API 方法
export default {
    // 钢筋检测
    analyze(formData, mode = 'spacing', conf = 40, overlap = 40, extraParams = {}) {
        let url = `/api/analyze?mode=${mode}&conf=${conf}&overlap=${overlap}`
        for (const [key, value] of Object.entries(extraParams)) {
            url += `&${encodeURIComponent(key)}=${encodeURIComponent(value)}`
        }
        return api.post(url, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
    },

    // CAD 图纸智能解析
    parseCad(formData) {
        return api.post('/api/parse_cad', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
    },

    // 原材微观核验（轧印识别）
    verifyMaterial(formData) {
        return api.post('/api/verify_material', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
    },

    // OCR 识别
    ocr(formData) {
        return api.post('/api/ocr', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
    },

    // 合规性检查
    checkCompliance(detectedCount, designTotal) {
        return api.post('/api/check_compliance', {
            detected_count: detectedCount,
            design_total: designTotal
        })
    },

    // 获取检测记录
    getRecords(page = 1, perPage = 20, type = null) {
        const params = { page, per_page: perPage }
        if (type) params.type = type
        return api.get('/api/records', { params })
    },

    // 创建检测记录
    createRecord(data) {
        return api.post('/api/records', data)
    },

    // 删除检测记录
    deleteRecord(id) {
        return api.delete(`/api/records/${id}`)
    },

    // 导出 Excel
    exportExcel(data) {
        return api.post('/api/export_excel', data, {
            responseType: 'blob'
        })
    },

    // 健康检查
    health() {
        return api.get('/api/health')
    }
}

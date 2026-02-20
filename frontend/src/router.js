import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: () => import('./views/Home.vue'),
        meta: { title: '首页' }
    },
    {
        path: '/workbench',
        name: 'WorkBench',
        component: () => import('./views/WorkBench.vue'),
        meta: { title: '平法智能工作台' }
    },
    {
        path: '/hidden-inspection',
        name: 'HiddenInspection',
        component: () => import('./views/HiddenInspection.vue'),
        meta: { title: '隐蔽工程验收' }
    },
    {
        path: '/inspection',
        name: 'Inspection',
        component: () => import('./views/Inspection.vue'),
        meta: { title: '进场材料验收' }
    },
    {
        path: '/records',
        name: 'Records',
        component: () => import('./views/Records.vue'),
        meta: { title: '检测记录' }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// 路由标题
router.beforeEach((to, from, next) => {
    document.title = `${to.meta.title || '钢筋检测'} - 钢筋工程智能管控平台`
    next()
})

export default router

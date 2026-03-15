import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: () => import('./views/Home.vue'),
        meta: { title: '首页' }
    },
    {
        path: '/hidden-inspection',
        name: 'HiddenInspection',
        component: () => import('./views/WorkBench.vue'),
        meta: { title: '隐蔽工程验收' }
    },
    {
        path: '/material-inspection',
        name: 'MaterialInspection',
        component: () => import('./views/MaterialInspection.vue'),
        meta: { title: '进场材料验收' }
    },
    {
        path: '/micro-inspection',
        name: 'MicroInspection',
        component: () => import('./views/MicroInspection.vue'),
        meta: { title: '原材微观检测' }
    },
    {
        path: '/records',
        name: 'Records',
        component: () => import('./views/Records.vue'),
        meta: { title: '检测数据中心' }
    },
    {
        // 兼容旧路由
        path: '/workbench',
        redirect: '/hidden-inspection'
    },
    {
        path: '/inspection',
        redirect: '/hidden-inspection'
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

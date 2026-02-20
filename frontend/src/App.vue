<script setup>
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* 暗色主题覆盖 Element Plus */
.el-card {
  --el-card-bg-color: #3a4556;
}

.el-input__wrapper,
.el-input-number,
.el-select .el-input__wrapper {
  background-color: #22252b !important;
  box-shadow: 0 0 0 1px #4a5568 inset !important;
}

.el-input__inner,
.el-input-number__decrease,
.el-input-number__increase {
  color: #e2e8f0 !important;
}

.el-upload-dragger {
  background-color: #22252b !important;
  border-color: #4a5568 !important;
}

.el-upload-dragger:hover {
  border-color: #409EFF !important;
}

.el-slider__runway {
  background-color: #4a5568 !important;
}

.el-form-item__label {
  color: #a0aec0 !important;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #2d3748;
}

::-webkit-scrollbar-thumb {
  background: #4a5568;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #5a6880;
}
</style>

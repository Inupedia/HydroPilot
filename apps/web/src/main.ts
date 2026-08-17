import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import App from './App.vue'
import './style.css'

createApp(App).use(createPinia()).mount('#app')

import React from 'react'
import ReactDOM from 'react-dom/client'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import App from './App'
import './style.css'

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

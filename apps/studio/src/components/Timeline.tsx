import { useCallback, useEffect, useMemo, useState } from 'react'
import { hydroApi, type FlowForecastResponse, type FlowObservation } from '../api/client'
import { demoForecastHistory, forecastChartGeometry, formatArrival, polylinePoints } from './forecastView'
import './forecast.css'

interface TimelineProps {
  timestamps: number[]
  timestamp: number
  onChange: (value: number) => void
}

const CHART_WIDTH = 640
const CHART_HEIGHT = 150

export default function Timeline({ timestamps, timestamp, onChange }: TimelineProps) {
  const [history, setHistory] = useState<FlowObservation[]>([])
  const [forecast, setForecast] = useState<FlowForecastResponse | null>(null)
  const [forecastBusy, setForecastBusy] = useState(false)
  const [forecastError, setForecastError] = useState('')

  const loadForecast = useCallback(async () => {
    setForecastBusy(true)
    setForecastError('')
    try {
      const objects = await hydroApi.objects()
      const gauge = objects.find((item) => item.id === 'gauge-keswick')
      const currentFlow = Number(gauge?.properties.latest_flow_cms)
      if (!Number.isFinite(currentFlow) || currentFlow < 0) {
        throw new Error('gauge-keswick requires a non-negative latest_flow_cms demo value')
      }
      const nextHistory = demoForecastHistory(currentFlow)
      const nextForecast = await hydroApi.flowForecast({
        object_id: 'gauge-keswick',
        history: nextHistory,
        horizon_minutes: 180,
        dt_minutes: 30,
        model: 'damped_trend',
        trend_window_points: 4,
        damping: 0.82,
      })
      setHistory(nextHistory)
      setForecast(nextForecast)
    } catch (error) {
      setForecastError(error instanceof Error ? error.message : String(error))
    } finally {
      setForecastBusy(false)
    }
  }, [])

  useEffect(() => { void loadForecast() }, [loadForecast])

  const geometry = useMemo(() => {
    if (!forecast || !history.length) return null
    return forecastChartGeometry(history, forecast.forecast, CHART_WIDTH, CHART_HEIGHT)
  }, [forecast, history])

  if (!timestamps.length) return null
  const min = timestamps[0]
  const max = timestamps[timestamps.length - 1]
  const step = Math.max(1, timestamps[1] ? timestamps[1] - timestamps[0] : 30)
  const summary = forecast?.summary
  const peakChange = summary?.peak_change_pct == null ? null : `${summary.peak_change_pct >= 0 ? '+' : ''}${summary.peak_change_pct.toFixed(1)}% vs now`
  const nowLeft = geometry ? `${(geometry.nowX / CHART_WIDTH) * 100}%` : '33.3%'

  return (
    <div className="timeline forecast-timeline" data-testid="timeline">
      <div className="forecast-topline">
        <div className="forecast-heading">
          <div>
            <small>FLOW FORECAST · KESWICK GAUGE</small>
            <strong>Observed → NOW → predicted</strong>
          </div>
        </div>
        <span className={`forecast-badge ${forecastBusy ? 'loading' : ''}`}>
          {forecastBusy ? 'Forecasting…' : forecast ? forecast.model.replace('_', ' ') : 'Unavailable'}
        </span>
      </div>

      {forecastError ? <div className="forecast-error" role="alert">Forecast unavailable: {forecastError}</div> : null}

      <div className="forecast-summary-grid" aria-label="Forecast summary">
        <article className="forecast-stat">
          <span>Current flow</span>
          <strong>{summary ? `${summary.current_flow_cms.toFixed(0)} m³/s` : '—'}</strong>
          <small>NOW · fixture gauge</small>
        </article>
        <article className="forecast-stat">
          <span>Forecast peak</span>
          <strong>{summary ? `${summary.peak_flow_cms.toFixed(0)} m³/s` : '—'}</strong>
          <small>{peakChange ?? 'waiting for forecast'}</small>
        </article>
        <article className="forecast-stat">
          <span>Peak arrival</span>
          <strong>{summary ? formatArrival(summary.peak_timestamp_minutes) : '—'}</strong>
          <small>{summary ? summary.trend.toUpperCase() : 'future horizon'}</small>
        </article>
      </div>

      <div className="forecast-chart-wrap" data-testid="forecast-chart">
        {geometry ? (
          <>
            <svg className="forecast-chart" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} preserveAspectRatio="none" aria-label="Observed and forecast flow chart" role="img">
              {[0.25, 0.5, 0.75].map((fraction) => <line key={fraction} className="forecast-grid-line" x1="0" x2={CHART_WIDTH} y1={CHART_HEIGHT * fraction} y2={CHART_HEIGHT * fraction}/>) }
              <line className="forecast-now-line" x1={geometry.nowX} x2={geometry.nowX} y1="0" y2={CHART_HEIGHT}/>
              <polyline className="forecast-observed-line" points={polylinePoints(geometry.observed)}/>
              <polyline className="forecast-predicted-line" points={polylinePoints(geometry.forecast)}/>
            </svg>
            <span className="forecast-now-label" style={{ left: nowLeft }}>NOW</span>
          </>
        ) : null}
      </div>

      <div className="forecast-legend-row">
        <div className="forecast-series-legend"><span><i/>Observed</span><span><i className="predicted"/>Forecast</span></div>
        <span className="forecast-provenance">Demo-only history is derived from the fixture latest flow to exercise the forecast API; not operational observations.</span>
      </div>

      <div className="forecast-scenario-row">
        <span>0D + 1D scenario · t = {timestamp} min</span>
        <input
          aria-label="Scenario time"
          type="range"
          min={min}
          max={max}
          step={step}
          value={timestamp}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        <button className="forecast-refresh" type="button" disabled={forecastBusy} onClick={() => void loadForecast()}>
          {forecastBusy ? 'Refreshing…' : 'Refresh forecast'}
        </button>
      </div>
    </div>
  )
}

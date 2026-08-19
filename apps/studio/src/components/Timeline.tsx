import { useCallback, useEffect, useMemo, useState } from 'react'
import { hydroApi, type FlowObservation, type RunoffForecastResponse } from '../api/client'
import { demoForecastHistory, demoRainfallForecast, forecastChartGeometry, formatArrival, polylinePoints } from './forecastView'
import './forecast.css'

interface TimelineProps {
  timestamps: number[]
  timestamp: number
  onChange: (value: number) => void
}

const CHART_WIDTH = 640
const CHART_HEIGHT = 150
const CATCHMENT_AREA_KM2 = 1200
const RUNOFF_COEFFICIENT = 0.18
const RESPONSE_TIME_HOURS = 8

export default function Timeline({ timestamps, timestamp, onChange }: TimelineProps) {
  const [history, setHistory] = useState<FlowObservation[]>([])
  const [forecast, setForecast] = useState<RunoffForecastResponse | null>(null)
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
      const rainfall = demoRainfallForecast()
      const nextForecast = await hydroApi.runoffForecast({
        object_id: 'gauge-keswick',
        rainfall,
        dt_minutes: 30,
        initial_flow_cms: currentFlow,
        catchment_area_km2: CATCHMENT_AREA_KM2,
        runoff_coefficient: RUNOFF_COEFFICIENT,
        response_time_hours: RESPONSE_TIME_HOURS,
        baseflow_cms: currentFlow * 0.57,
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
    return forecastChartGeometry(history, forecast.runoff, CHART_WIDTH, CHART_HEIGHT)
  }, [forecast, history])

  const hasScenario = timestamps.length > 0
  const min = timestamps[0] ?? 0
  const max = timestamps[timestamps.length - 1] ?? 180
  const step = Math.max(1, timestamps[1] ? timestamps[1] - timestamps[0] : 30)
  const summary = forecast?.summary
  const peakChange = summary?.peak_change_pct == null ? null : `${summary.peak_change_pct >= 0 ? '+' : ''}${summary.peak_change_pct.toFixed(1)}% vs now`
  const nowLeft = geometry ? `${(geometry.nowX / CHART_WIDTH) * 100}%` : '33.3%'
  const rainfallMax = Math.max(1, ...(forecast?.runoff.map((point) => point.rainfall_mm) ?? [1]))

  return (
    <div className="timeline forecast-timeline" data-testid="timeline">
      <div className="forecast-topline">
        <div className="forecast-heading">
          <div>
            <small>RAINFALL → RUNOFF FORECAST · KESWICK</small>
            <strong>Observed flow → NOW → rainfall-driven flow</strong>
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
          <span>Rain-driven peak</span>
          <strong>{summary ? `${summary.peak_flow_cms.toFixed(0)} m³/s` : '—'}</strong>
          <small>{peakChange ?? 'waiting for forecast'}</small>
        </article>
        <article className="forecast-stat">
          <span>Peak arrival</span>
          <strong>{summary ? formatArrival(summary.peak_timestamp_minutes) : '—'}</strong>
          <small>{summary ? `${summary.total_rainfall_mm.toFixed(0)} mm forecast rain` : 'future horizon'}</small>
        </article>
      </div>

      <div className="forecast-chart-wrap" data-testid="forecast-chart">
        {geometry ? (
          <>
            <svg className="forecast-chart" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} preserveAspectRatio="none" aria-label="Observed and rainfall-driven forecast flow chart" role="img">
              {[0.25, 0.5, 0.75].map((fraction) => <line key={fraction} className="forecast-grid-line" x1="0" x2={CHART_WIDTH} y1={CHART_HEIGHT * fraction} y2={CHART_HEIGHT * fraction}/>) }
              <line className="forecast-now-line" x1={geometry.nowX} x2={geometry.nowX} y1="0" y2={CHART_HEIGHT}/>
              <polyline className="forecast-observed-line" points={polylinePoints(geometry.observed)}/>
              <polyline className="forecast-predicted-line" points={polylinePoints(geometry.forecast)}/>
            </svg>
            <span className="forecast-now-label" style={{ left: nowLeft }}>NOW</span>
          </>
        ) : null}
      </div>

      <div className="rainfall-strip" data-testid="rainfall-strip" aria-label="Forecast rainfall profile">
        <div className="rainfall-strip-label"><strong>Forecast rainfall</strong><small>drives runoff model</small></div>
        <div className="rainfall-bars">
          {forecast?.runoff.map((point) => (
            <div className="rainfall-step" key={point.timestamp_minutes}>
              <div className="rainfall-bar-track"><i style={{ height: `${Math.max(3, (point.rainfall_mm / rainfallMax) * 100)}%` }}/></div>
              <span>{point.rainfall_mm.toFixed(0)}</span>
              <small>+{point.timestamp_minutes / 60}h</small>
            </div>
          ))}
        </div>
        <div className="rainfall-total"><strong>{summary ? `${summary.total_rainfall_mm.toFixed(0)} mm` : '—'}</strong><small>3h total</small></div>
      </div>

      <div className="forecast-legend-row">
        <div className="forecast-series-legend"><span><i/>Observed</span><span><i className="predicted"/>Rainfall-driven forecast</span></div>
        <span className="forecast-provenance">Demo rainfall + uncalibrated basin assumptions ({CATCHMENT_AREA_KM2.toLocaleString()} km² · C={RUNOFF_COEFFICIENT} · K={RESPONSE_TIME_HOURS}h). History is derived from fixture latest flow; not operational data.</span>
      </div>

      {hasScenario ? (
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
            {forecastBusy ? 'Refreshing…' : 'Refresh runoff forecast'}
          </button>
        </div>
      ) : (
        <div className="forecast-scenario-row scenario-empty">
          <span>Forecast is live in the demo · run a release scenario to enable 0D + 1D playback.</span>
          <button className="forecast-refresh" type="button" disabled={forecastBusy} onClick={() => void loadForecast()}>
            {forecastBusy ? 'Refreshing…' : 'Refresh runoff forecast'}
          </button>
        </div>
      )}
    </div>
  )
}

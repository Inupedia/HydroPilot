import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { hydroApi, type FlowObservation, type ReservoirRainfallForecastResponse } from '../api/client'
import { forecastTimestamps } from '../cesium/forecastScene'
import type { HydroState } from '../types'
import { demoForecastHistory, demoRainfallForecast, forecastChartGeometry, formatArrival, polylinePoints } from './forecastView'
import './forecast.css'

export type ScenePreviewMode = 'forecast' | 'scenario'

interface TimelineProps {
  timestamps: number[]
  timestamp: number
  inflowCms: number
  releaseCms: number
  forecastTimestamp: number
  sceneMode: ScenePreviewMode
  onChange: (value: number) => void
  onForecastStates: (states: HydroState[]) => void
  onForecastTimestampChange: (value: number) => void
  onSceneModeChange: (mode: ScenePreviewMode) => void
}

const CHART_WIDTH = 640
const CHART_HEIGHT = 150
const CATCHMENT_AREA_KM2 = 8000
const RUNOFF_COEFFICIENT = 0.18
const RESPONSE_TIME_HOURS = 8

export default function Timeline({
  timestamps,
  timestamp,
  inflowCms,
  releaseCms,
  forecastTimestamp,
  sceneMode,
  onChange,
  onForecastStates,
  onForecastTimestampChange,
  onSceneModeChange,
}: TimelineProps) {
  const requestVersion = useRef(0)
  const [history, setHistory] = useState<FlowObservation[]>([])
  const [forecast, setForecast] = useState<ReservoirRainfallForecastResponse | null>(null)
  const [forecastBusy, setForecastBusy] = useState(false)
  const [forecastError, setForecastError] = useState('')
  const [forecastPlaying, setForecastPlaying] = useState(false)

  const loadForecast = useCallback(async () => {
    const version = ++requestVersion.current
    setForecastBusy(true)
    setForecastError('')
    try {
      if (!Number.isFinite(inflowCms) || inflowCms < 0) throw new Error('reservoir inflow must be non-negative')
      if (!Number.isFinite(releaseCms) || releaseCms < 0) throw new Error('reservoir release must be non-negative')
      const nextHistory = demoForecastHistory(inflowCms)
      const rainfall = demoRainfallForecast()
      const nextForecast = await hydroApi.reservoirForecast({
        reservoir_id: 'reservoir-shasta',
        rainfall,
        dt_minutes: 30,
        initial_inflow_cms: inflowCms,
        release_cms: releaseCms,
        catchment_area_km2: CATCHMENT_AREA_KM2,
        runoff_coefficient: RUNOFF_COEFFICIENT,
        response_time_hours: RESPONSE_TIME_HOURS,
        baseflow_cms: inflowCms * 0.57,
        max_hops: 12,
      })
      if (version !== requestVersion.current) return
      const nextTimes = forecastTimestamps(nextForecast.scenario.states)
      setHistory(nextHistory)
      setForecast(nextForecast)
      onForecastStates(nextForecast.scenario.states)
      onForecastTimestampChange(nextTimes[0] ?? 0)
      onSceneModeChange('forecast')
    } catch (error) {
      if (version !== requestVersion.current) return
      setForecastError(error instanceof Error ? error.message : String(error))
    } finally {
      if (version === requestVersion.current) setForecastBusy(false)
    }
  }, [inflowCms, releaseCms, onForecastStates, onForecastTimestampChange, onSceneModeChange])

  useEffect(() => { void loadForecast() }, [loadForecast])

  const geometry = useMemo(() => {
    if (!forecast || !history.length) return null
    return forecastChartGeometry(history, forecast.runoff.runoff, CHART_WIDTH, CHART_HEIGHT)
  }, [forecast, history])
  const previewTimes = useMemo(() => forecastTimestamps(forecast?.scenario.states ?? []), [forecast])

  useEffect(() => {
    if (!forecastPlaying || !previewTimes.length) return
    const timer = window.setInterval(() => {
      onSceneModeChange('forecast')
      const index = previewTimes.indexOf(forecastTimestamp)
      const nextIndex = index < 0 || index >= previewTimes.length - 1 ? 0 : index + 1
      onForecastTimestampChange(previewTimes[nextIndex])
    }, 900)
    return () => window.clearInterval(timer)
  }, [forecastPlaying, forecastTimestamp, onForecastTimestampChange, onSceneModeChange, previewTimes])

  const hasScenario = timestamps.length > 0
  const min = timestamps[0] ?? 0
  const max = timestamps[timestamps.length - 1] ?? 180
  const step = Math.max(1, timestamps[1] ? timestamps[1] - timestamps[0] : 30)
  const previewMin = previewTimes[0] ?? 0
  const previewMax = previewTimes[previewTimes.length - 1] ?? 180
  const previewStep = Math.max(1, previewTimes[1] ? previewTimes[1] - previewTimes[0] : 30)
  const runoffSummary = forecast?.runoff.summary
  const reservoirSummary = forecast?.summary
  const peakChange = runoffSummary?.peak_change_pct == null ? null : `${runoffSummary.peak_change_pct >= 0 ? '+' : ''}${runoffSummary.peak_change_pct.toFixed(1)}% vs now`
  const storageChange = reservoirSummary?.storage_change_pct == null ? null : `${reservoirSummary.storage_change_pct >= 0 ? '+' : ''}${reservoirSummary.storage_change_pct.toFixed(2)}%`
  const levelStatus = reservoirSummary?.final_level_m == null ? 'level unavailable' : `level ${reservoirSummary.final_level_m.toFixed(2)} m`
  const nowLeft = geometry ? `${(geometry.nowX / CHART_WIDTH) * 100}%` : '33.3%'
  const rainfallMax = Math.max(1, ...(forecast?.runoff.runoff.map((point) => point.rainfall_mm) ?? [1]))

  return (
    <div className="timeline forecast-timeline" data-testid="timeline">
      <div className="forecast-topline">
        <div className="forecast-heading">
          <div>
            <small>RAINFALL → RESERVOIR FORECAST · SHASTA</small>
            <strong>Forecast inflow → storage under {releaseCms.toLocaleString()} m³/s release</strong>
          </div>
        </div>
        <span className={`forecast-badge ${forecastBusy ? 'loading' : ''}`}>
          {forecastBusy ? 'Forecasting…' : forecast ? 'reservoir balance' : 'Unavailable'}
        </span>
      </div>

      {forecastError ? <div className="forecast-error" role="alert">Forecast unavailable: {forecastError}</div> : null}

      <div className="forecast-summary-grid reservoir-summary-grid" aria-label="Forecast summary">
        <article className="forecast-stat">
          <span>Current inflow</span>
          <strong>{runoffSummary ? `${runoffSummary.current_flow_cms.toFixed(0)} m³/s` : '—'}</strong>
          <small>NOW · explicit boundary</small>
        </article>
        <article className="forecast-stat">
          <span>Rain-driven peak</span>
          <strong>{reservoirSummary ? `${reservoirSummary.peak_inflow_cms.toFixed(0)} m³/s` : '—'}</strong>
          <small>{peakChange ?? 'waiting for forecast'}</small>
        </article>
        <article className="forecast-stat">
          <span>Peak arrival</span>
          <strong>{reservoirSummary ? formatArrival(reservoirSummary.peak_inflow_timestamp_minutes) : '—'}</strong>
          <small>{runoffSummary ? `${runoffSummary.total_rainfall_mm.toFixed(0)} mm forecast rain` : 'future horizon'}</small>
        </article>
        <article className="forecast-stat reservoir-storage-stat">
          <span>3h reservoir storage</span>
          <strong>{reservoirSummary ? `${(reservoirSummary.final_storage_m3 / 1e9).toFixed(3)} B m³` : '—'}</strong>
          <small>{storageChange ? `${storageChange} · ${levelStatus}` : 'no level-storage curve'}</small>
        </article>
      </div>

      <div className="forecast-chart-wrap" data-testid="forecast-chart">
        {geometry ? (
          <>
            <svg className="forecast-chart" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} preserveAspectRatio="none" aria-label="Observed and rainfall-driven reservoir inflow forecast chart" role="img">
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
        <div className="rainfall-strip-label"><strong>Forecast rainfall</strong><small>drives reservoir inflow</small></div>
        <div className="rainfall-bars">
          {forecast?.runoff.runoff.map((point) => (
            <div className="rainfall-step" key={point.timestamp_minutes}>
              <div className="rainfall-bar-track"><i style={{ height: `${Math.max(3, (point.rainfall_mm / rainfallMax) * 100)}%` }}/></div>
              <span>{point.rainfall_mm.toFixed(0)}</span>
              <small>+{point.timestamp_minutes / 60}h</small>
            </div>
          ))}
        </div>
        <div className="rainfall-total"><strong>{runoffSummary ? `${runoffSummary.total_rainfall_mm.toFixed(0)} mm` : '—'}</strong><small>3h total</small></div>
      </div>

      <div className="cesium-preplay" data-testid="cesium-preplay">
        <div className="cesium-preplay-heading"><strong>CESIUM 3D PREPLAY</strong><small>flow walls · glow ribbons · reservoir volume</small></div>
        <div className="preplay-mode-switch" aria-label="3D scene mode">
          <button className={sceneMode === 'forecast' ? 'active' : ''} type="button" onClick={() => onSceneModeChange('forecast')}>Forecast</button>
          <button className={sceneMode === 'scenario' ? 'active' : ''} type="button" disabled={!hasScenario} onClick={() => { setForecastPlaying(false); onSceneModeChange('scenario') }}>Scenario</button>
        </div>
        <button className={`preplay-play ${forecastPlaying ? 'active' : ''}`} type="button" disabled={!previewTimes.length} onClick={() => { onSceneModeChange('forecast'); setForecastPlaying((value) => !value) }}>
          {forecastPlaying ? 'Pause' : '▶ Play'}
        </button>
        <input
          aria-label="Forecast 3D preview time"
          type="range"
          min={previewMin}
          max={previewMax}
          step={previewStep}
          value={forecastTimestamp}
          disabled={!previewTimes.length}
          onChange={(event) => { setForecastPlaying(false); onSceneModeChange('forecast'); onForecastTimestampChange(Number(event.target.value)) }}
        />
        <span className="preplay-time">T+{forecastTimestamp} min</span>
      </div>

      <div className="forecast-legend-row">
        <div className="forecast-series-legend"><span><i/>Demo pre-NOW inflow</span><span><i className="predicted"/>Rainfall-driven inflow</span></div>
        <span className="forecast-provenance">Demo rainfall + uncalibrated basin assumptions ({CATCHMENT_AREA_KM2.toLocaleString()} km² · C={RUNOFF_COEFFICIENT} · K={RESPONSE_TIME_HOURS}h). Pre-NOW history is scaled from the explicit inflow boundary. No reservoir level is forecast without a level-storage curve.</span>
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
            onChange={(event) => { setForecastPlaying(false); onSceneModeChange('scenario'); onChange(Number(event.target.value)) }}
          />
          <button className="forecast-refresh" type="button" disabled={forecastBusy} onClick={() => void loadForecast()}>
            {forecastBusy ? 'Refreshing…' : 'Refresh reservoir forecast'}
          </button>
        </div>
      ) : (
        <div className="forecast-scenario-row scenario-empty">
          <span>Reservoir forecast is live · run the explicit scenario to enable 0D + 1D playback.</span>
          <button className="forecast-refresh" type="button" disabled={forecastBusy} onClick={() => void loadForecast()}>
            {forecastBusy ? 'Refreshing…' : 'Refresh reservoir forecast'}
          </button>
        </div>
      )}
    </div>
  )
}

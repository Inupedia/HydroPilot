import type { FlowForecastPoint, FlowObservation, RainfallForecastPoint } from '../api/client'

export interface ChartPoint {
  timestamp_minutes: number
  flow_cms: number
  x: number
  y: number
}

export interface ForecastChartGeometry {
  observed: ChartPoint[]
  forecast: ChartPoint[]
  nowX: number
  minFlow: number
  maxFlow: number
}

export function demoForecastHistory(currentFlowCms: number): FlowObservation[] {
  const current = Math.max(0, currentFlowCms)
  return [
    { timestamp_minutes: -90, flow_cms: current * 0.78 },
    { timestamp_minutes: -60, flow_cms: current * 0.86 },
    { timestamp_minutes: -30, flow_cms: current * 0.93 },
    { timestamp_minutes: 0, flow_cms: current },
  ]
}

export function demoRainfallForecast(): RainfallForecastPoint[] {
  return [0, 3, 8, 14, 7, 2].map((precipitation_mm, index) => ({
    timestamp_minutes: (index + 1) * 30,
    precipitation_mm,
  }))
}

export function forecastChartGeometry(
  history: FlowObservation[],
  forecast: FlowForecastPoint[],
  width = 640,
  height = 150,
): ForecastChartGeometry {
  if (!history.length) throw new Error('forecast chart requires history')
  if (!forecast.length) throw new Error('forecast chart requires forecast points')

  const all = [...history, ...forecast]
  const minTime = Math.min(...all.map((point) => point.timestamp_minutes))
  const maxTime = Math.max(...all.map((point) => point.timestamp_minutes))
  const rawMinFlow = Math.min(...all.map((point) => point.flow_cms))
  const rawMaxFlow = Math.max(...all.map((point) => point.flow_cms))
  const flowPadding = Math.max(1, (rawMaxFlow - rawMinFlow) * 0.14)
  const minFlow = Math.max(0, rawMinFlow - flowPadding)
  const maxFlow = rawMaxFlow + flowPadding
  const timeSpan = Math.max(1, maxTime - minTime)
  const flowSpan = Math.max(1, maxFlow - minFlow)
  const xFor = (minutes: number) => ((minutes - minTime) / timeSpan) * width
  const yFor = (flow: number) => height - ((flow - minFlow) / flowSpan) * height
  const mapPoint = (point: FlowObservation | FlowForecastPoint): ChartPoint => ({
    timestamp_minutes: point.timestamp_minutes,
    flow_cms: point.flow_cms,
    x: xFor(point.timestamp_minutes),
    y: yFor(point.flow_cms),
  })

  const observed = history.map(mapPoint)
  const current = history[history.length - 1]
  const forecastSeries = [current, ...forecast].map(mapPoint)
  return {
    observed,
    forecast: forecastSeries,
    nowX: xFor(0),
    minFlow,
    maxFlow,
  }
}

export function polylinePoints(points: ChartPoint[]): string {
  return points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' ')
}

export function formatArrival(minutes: number): string {
  if (minutes < 60) return `+${minutes} min`
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return remainder ? `+${hours}h ${remainder}m` : `+${hours}h`
}

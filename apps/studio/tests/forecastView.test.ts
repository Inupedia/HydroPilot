import { describe, expect, it } from 'vitest'
import { demoForecastHistory, forecastChartGeometry, formatArrival, polylinePoints } from '../src/components/forecastView'


describe('forecast timeline helpers', () => {
  it('builds a rising demo history that ends exactly at NOW', () => {
    const history = demoForecastHistory(210)

    expect(history.map((point) => point.timestamp_minutes)).toEqual([-90, -60, -30, 0])
    expect(history.at(-1)?.flow_cms).toBe(210)
    expect(history[0].flow_cms).toBeLessThan(history.at(-1)!.flow_cms)
  })

  it('keeps NOW as the join between observed and forecast lines', () => {
    const history = demoForecastHistory(200)
    const forecast = [
      { timestamp_minutes: 30, flow_cms: 220 },
      { timestamp_minutes: 60, flow_cms: 235 },
    ]
    const geometry = forecastChartGeometry(history, forecast, 600, 120)

    expect(geometry.observed.at(-1)?.timestamp_minutes).toBe(0)
    expect(geometry.forecast[0].timestamp_minutes).toBe(0)
    expect(geometry.forecast[1].timestamp_minutes).toBe(30)
    expect(geometry.nowX).toBe(geometry.observed.at(-1)?.x)
    expect(polylinePoints(geometry.forecast)).toContain(',')
  })

  it('formats forecast arrival offsets for minutes and hours', () => {
    expect(formatArrival(30)).toBe('+30 min')
    expect(formatArrival(60)).toBe('+1h')
    expect(formatArrival(150)).toBe('+2h 30m')
  })
})

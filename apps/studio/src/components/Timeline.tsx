interface TimelineProps {
  timestamps: number[]
  timestamp: number
  onChange: (value: number) => void
}

export default function Timeline({ timestamps, timestamp, onChange }: TimelineProps) {
  if (!timestamps.length) return null
  const min = timestamps[0]
  const max = timestamps[timestamps.length - 1]
  return (
    <div className="timeline" data-testid="timeline">
      <span>0D + 1D routing</span>
      <input
        aria-label="Scenario time"
        type="range"
        min={min}
        max={max}
        step={Math.max(1, timestamps[1] ? timestamps[1] - timestamps[0] : 30)}
        value={timestamp}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <span>t = {timestamp} min</span>
    </div>
  )
}

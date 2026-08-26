import { useCallback, useRef } from 'react'
import { Button, Typography } from 'antd'
import { CheckCircleFilled, LeftOutlined, RightOutlined } from '@ant-design/icons'
import {
  hardwarePixelArtUrl,
  UNKNOWN_HARDWARE_PIXELART_URL,
} from '@/utils/hardwarePixelArt'

export interface DeviceSourceOption {
  value: string
  label: string
}

interface DeviceSourceCarouselProps {
  options: DeviceSourceOption[]
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

function toDisplayName(label: string): string {
  return label.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function DeviceSourceCarousel({
  options,
  value,
  onChange,
  disabled = false,
}: DeviceSourceCarouselProps) {
  const trackRef = useRef<HTMLDivElement>(null)

  const scrollByPage = useCallback((dir: -1 | 1) => {
    const track = trackRef.current
    if (!track) return
    const card = track.querySelector<HTMLElement>('.device-card')
    const step = card
      ? Math.max(card.offsetWidth + 12, Math.round(track.clientWidth * 0.75))
      : Math.round(track.clientWidth * 0.8)
    track.scrollBy({ left: dir * step, behavior: 'smooth' })
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (disabled || options.length === 0) return
      const idx = options.findIndex((o) => o.value === value)
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        const next = options[Math.min(idx + 1, options.length - 1)]
        if (next) onChange(next.value)
        scrollByPage(1)
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        const prev = options[Math.max(idx - 1, 0)]
        if (prev) onChange(prev.value)
        scrollByPage(-1)
      }
    },
    [disabled, options, value, onChange, scrollByPage],
  )

  return (
    <div className="device-source-carousel">
      <Button
        type="text"
        aria-label="Previous devices"
        icon={<LeftOutlined />}
        className="device-source-carousel-arrow"
        onClick={() => scrollByPage(-1)}
        disabled={disabled}
      />
      <div
        ref={trackRef}
        className="device-source-carousel-track"
        role="listbox"
        tabIndex={0}
        aria-label="Device type"
        onKeyDown={handleKeyDown}
      >
        {options.map((opt) => {
          const selected = opt.value === value
          return (
            <button
              key={opt.value}
              type="button"
              role="option"
              aria-selected={selected}
              className={`device-card${selected ? ' selected' : ''}`}
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              title={toDisplayName(opt.label)}
            >
              {selected && <CheckCircleFilled className="device-card-check" aria-hidden />}
              <span className="device-card-image">
                <img
                  src={hardwarePixelArtUrl(opt.value)}
                  alt={opt.label}
                  loading="lazy"
                  draggable={false}
                  onError={(e) => {
                    const img = e.currentTarget
                    if (img.src !== UNKNOWN_HARDWARE_PIXELART_URL) {
                      img.src = UNKNOWN_HARDWARE_PIXELART_URL
                    }
                  }}
                />
              </span>
              <span className="device-card-label">
                <Typography.Text strong>{toDisplayName(opt.label)}</Typography.Text>
              </span>
            </button>
          )
        })}
      </div>
      <Button
        type="text"
        aria-label="Next devices"
        icon={<RightOutlined />}
        className="device-source-carousel-arrow"
        onClick={() => scrollByPage(1)}
        disabled={disabled}
      />
    </div>
  )
}

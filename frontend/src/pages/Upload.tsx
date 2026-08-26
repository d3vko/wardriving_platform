import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  List,
  Progress,
  Space,
  Tag,
  Typography,
  message,
} from 'antd'
import {
  CheckCircleOutlined,
  CloseOutlined,
  CloudUploadOutlined,
  FileOutlined,
} from '@ant-design/icons'
import { getDeviceSources, MAX_UPLOAD_FILES, uploadFiles } from '@/api/files'
import type { DeviceSource } from '@/api/files'
import DeviceSourceCarousel from '@/components/DeviceSourceCarousel'
import { ApiError } from '@/api/client'

interface UploadResult {
  filename: string
  ok: boolean
  detail?: string
}

export default function Upload() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [deviceSources, setDeviceSources] = useState<DeviceSource[]>([])
  const [deviceSource, setDeviceSource] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ done: number; total: number } | null>(null)
  const [results, setResults] = useState<UploadResult[] | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)

  useEffect(() => {
    getDeviceSources()
      .then((res) => {
        setDeviceSources(res.device_source)
        if (res.device_source.length > 0) setDeviceSource(res.device_source[0].value)
      })
      .catch(() => {
        /* ignore */
      })
  }, [])

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const arr = Array.from(newFiles)
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name))
      return [...prev, ...arr.filter((f) => !names.has(f.name))]
    })
    setResults(null)
  }, [])

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
    setResults(null)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files) addFiles(e.dataTransfer.files)
  }

  const handleSubmit = async () => {
    if (!deviceSource) {
      setFieldError('Select a device type')
      return
    }
    if (files.length === 0) {
      setFieldError('Add at least one file')
      return
    }
    setFieldError(null)
    setLoading(true)
    setUploadProgress({ done: 0, total: files.length })
    setResults(null)
    try {
      const uploaded = await uploadFiles(files, deviceSource, (done, total) => {
        setUploadProgress({ done, total })
      })
      const res: UploadResult[] = uploaded.map((u, i) => ({
        filename: files[i]?.name ?? u.source,
        ok: true,
      }))
      setResults(res)
      setFiles([])
      void message.success(`${uploaded.length} file(s) uploaded successfully`)
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : 'Failed to upload files'
      void message.error(msg)
    } finally {
      setLoading(false)
      setUploadProgress(null)
    }
  }

  return (
    <div className="upload-page">
      <div className="page-title-row">
        <CloudUploadOutlined style={{ fontSize: 32, color: 'var(--ant-color-primary)' }} />
        <Typography.Title level={2} style={{ margin: 0 }}>
          Upload files
        </Typography.Title>
      </div>
      <Typography.Paragraph type="secondary" className="page-lead">
        Upload wardriving capture logs. Multiple files are accepted at once.
      </Typography.Paragraph>

      <Space direction="vertical" size="large" className="upload-page-body">
        <div className="upload-device-section">
          <Typography.Text>Device type</Typography.Text>
          <div className="upload-device-carousel-wrap">
            <DeviceSourceCarousel
              options={deviceSources}
              value={deviceSource}
              onChange={setDeviceSource}
              disabled={loading}
            />
          </div>
          <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
            {fieldError && !deviceSource ? (
              fieldError
            ) : (
              <>
                WiGLE CSV (first line <code>WigleWifi-…</code>): choose Minino, RF Wi‑Fi, or Pwnterrey Marauder.
                Flipper / Marauder device types are for wardrive log files, not WiGLE spreadsheet exports.
              </>
            )}
          </Typography.Paragraph>
        </div>

        <div
          className={`upload-dropzone${dragging ? ' active' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => !loading && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => e.target.files && addFiles(e.target.files)}
          />
          <CloudUploadOutlined style={{ fontSize: 48, marginBottom: 8, opacity: 0.45 }} />
          <Typography.Paragraph strong>Drag files here or click to browse</Typography.Paragraph>
          <Typography.Paragraph type="secondary">
            You can select multiple files. Uploads larger than {MAX_UPLOAD_FILES} files are sent in batches.
          </Typography.Paragraph>
        </div>

        {files.length > 0 && (
          <Card title={`Selected files (${files.length})`}>
            <List
              dataSource={files}
              renderItem={(f, i) => (
                <List.Item
                  actions={[
                    <Tag key="size">{`${(f.size / 1024).toFixed(0)} KB`}</Tag>,
                    <Button key="rm" type="text" icon={<CloseOutlined />} disabled={loading} onClick={() => removeFile(i)} />,
                  ]}
                >
                  <Space>
                    <FileOutlined />
                    <Typography.Text ellipsis>{f.name}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        )}

        {fieldError && files.length === 0 && <Alert type="warning" showIcon message={fieldError} />}

        {results && (
          <Card
            title={
              <Space>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                Upload result
              </Space>
            }
          >
            {results.map((r) => (
              <Space key={r.filename}>
                <CheckCircleOutlined style={{ color: r.ok ? '#52c41a' : '#ff4d4f' }} />
                <Typography.Text>{r.filename}</Typography.Text>
              </Space>
            ))}
          </Card>
        )}

        {loading && (
          <div>
            <Progress
              percent={uploadProgress ? Math.round((uploadProgress.done / uploadProgress.total) * 100) : undefined}
              status="active"
            />
            {uploadProgress && (
              <Typography.Text type="secondary">
                Uploading {uploadProgress.done}/{uploadProgress.total} files
              </Typography.Text>
            )}
          </div>
        )}

        <Button
          type="primary"
          size="large"
          onClick={() => void handleSubmit()}
          disabled={loading || files.length === 0 || !deviceSource}
          loading={loading}
          icon={<CloudUploadOutlined />}
        >
          {loading
            ? `Uploading… ${uploadProgress ? `(${uploadProgress.done}/${uploadProgress.total})` : ''}`
            : `Upload ${files.length > 0 ? `(${files.length})` : ''}`}
        </Button>
      </Space>
    </div>
  )
}

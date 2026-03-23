import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  FormHelperText,
  IconButton,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Snackbar,
  Stack,
  Typography,
} from '@mui/material'
import {
  CloudUpload as CloudUploadIcon,
  Close as CloseIcon,
  InsertDriveFile as FileIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material'
import { getDeviceSources, uploadFiles } from '@/api/files'
import type { DeviceSource } from '@/api/files'
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
  const [results, setResults] = useState<UploadResult[] | null>(null)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  })
  const [fieldError, setFieldError] = useState<string | null>(null)

  useEffect(() => {
    getDeviceSources().then((res) => {
      setDeviceSources(res.device_source)
      if (res.device_source.length > 0) setDeviceSource(res.device_source[0].value)
    }).catch(() => { /* ignore */ })
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
    if (!deviceSource) { setFieldError('Selecciona un tipo de dispositivo'); return }
    if (files.length === 0) { setFieldError('Agrega al menos un archivo'); return }
    setFieldError(null)
    setLoading(true)
    setResults(null)
    try {
      const uploaded = await uploadFiles(files, deviceSource)
      const res: UploadResult[] = uploaded.map((u, i) => ({
        filename: files[i]?.name ?? u.source,
        ok: true,
      }))
      setResults(res)
      setFiles([])
      setSnackbar({ open: true, message: `${uploaded.length} archivo(s) subido(s) correctamente`, severity: 'success' })
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : 'Error al subir archivos'
      setSnackbar({ open: true, message: msg, severity: 'error' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1.5} mb={1}>
        <CloudUploadIcon color="primary" sx={{ fontSize: 32 }} />
        <Typography variant="h4" fontWeight={700}>
          Subir archivos
        </Typography>
      </Stack>
      <Typography variant="body1" color="text.secondary" mb={4}>
        Sube archivos de captura de wardriving. Se aceptan multiples archivos simultaneamente.
      </Typography>

      <Stack spacing={3} maxWidth={640}>
        {/* Device source selector */}
        <FormControl fullWidth error={Boolean(fieldError && !deviceSource)}>
          <InputLabel>Tipo de dispositivo</InputLabel>
          <Select
            value={deviceSource}
            label="Tipo de dispositivo"
            onChange={(e) => setDeviceSource(e.target.value)}
            disabled={loading}
          >
            {deviceSources.map((ds) => (
              <MenuItem key={ds.value} value={ds.value}>
                {ds.label}
              </MenuItem>
            ))}
          </Select>
          {fieldError && !deviceSource && <FormHelperText>{fieldError}</FormHelperText>}
        </FormControl>

        {/* Drop zone */}
        <Box
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => !loading && fileInputRef.current?.click()}
          sx={{
            border: '2px dashed',
            borderColor: dragging ? 'primary.main' : 'divider',
            borderRadius: 2,
            p: 4,
            textAlign: 'center',
            cursor: loading ? 'not-allowed' : 'pointer',
            bgcolor: dragging ? 'action.hover' : 'background.paper',
            transition: 'all 0.15s',
            '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => e.target.files && addFiles(e.target.files)}
          />
          <CloudUploadIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="body1" fontWeight={500}>
            Arrastra archivos aqui o haz click para seleccionar
          </Typography>
          <Typography variant="body2" color="text.secondary" mt={0.5}>
            Puedes seleccionar multiples archivos
          </Typography>
        </Box>

        {/* File list */}
        {files.length > 0 && (
          <Card>
            <CardContent sx={{ pb: '12px !important' }}>
              <Typography variant="subtitle2" fontWeight={600} mb={1.5}>
                Archivos seleccionados ({files.length})
              </Typography>
              <Stack spacing={1}>
                {files.map((f, i) => (
                  <Stack key={f.name} direction="row" alignItems="center" spacing={1}>
                    <FileIcon fontSize="small" color="action" />
                    <Typography variant="body2" noWrap sx={{ flexGrow: 1 }}>
                      {f.name}
                    </Typography>
                    <Chip
                      label={`${(f.size / 1024).toFixed(0)} KB`}
                      size="small"
                      variant="outlined"
                    />
                    <IconButton size="small" onClick={() => removeFile(i)} disabled={loading}>
                      <CloseIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                ))}
              </Stack>
            </CardContent>
          </Card>
        )}

        {/* Error */}
        {fieldError && files.length === 0 && (
          <Alert severity="warning">{fieldError}</Alert>
        )}

        {/* Results */}
        {results && (
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={1} mb={1.5}>
                <CheckCircleIcon color="success" />
                <Typography variant="subtitle2" fontWeight={600}>
                  Resultado del upload
                </Typography>
              </Stack>
              <Stack spacing={0.5}>
                {results.map((r) => (
                  <Stack key={r.filename} direction="row" alignItems="center" spacing={1}>
                    <CheckCircleIcon fontSize="small" color={r.ok ? 'success' : 'error'} />
                    <Typography variant="body2">{r.filename}</Typography>
                  </Stack>
                ))}
              </Stack>
            </CardContent>
          </Card>
        )}

        {loading && <LinearProgress />}

        <Button
          variant="contained"
          size="large"
          onClick={handleSubmit}
          disabled={loading || files.length === 0 || !deviceSource}
          startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <CloudUploadIcon />}
          sx={{ alignSelf: 'flex-start' }}
        >
          {loading ? 'Subiendo...' : `Subir ${files.length > 0 ? `(${files.length})` : ''}`}
        </Button>
      </Stack>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}

import { apiFetch } from './client'

export interface DeviceSource {
  value: string
  label: string
}

export interface DeviceSourcesResponse {
  device_source: DeviceSource[]
}

export interface FileUploaded {
  id: number
  source: string
  created_at: string
  uploaded_by: string
  device_source: string
  is_procesed: boolean
  hash_sha256: string | null
}

export const MAX_UPLOAD_FILES = 100

export function getDeviceSources(): Promise<DeviceSourcesResponse> {
  return apiFetch<DeviceSourcesResponse>('/device-sources/', { skipAuth: true })
}

function uploadFilesBatch(files: File[], deviceSource: string): Promise<FileUploaded[]> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('device_source', deviceSource)

  return apiFetch<FileUploaded[]>('/files-uploaded/', {
    method: 'POST',
    body: form,
  })
}

export async function uploadFiles(
  files: File[],
  deviceSource: string,
  onBatchProgress?: (done: number, total: number) => void,
): Promise<FileUploaded[]> {
  const uploaded: FileUploaded[] = []
  const total = files.length
  let done = 0

  if (total === 0) return uploaded

  for (let start = 0; start < total; start += MAX_UPLOAD_FILES) {
    const batch = files.slice(start, start + MAX_UPLOAD_FILES)
    const batchUploaded = await uploadFilesBatch(batch, deviceSource)
    uploaded.push(...batchUploaded)
    done += batch.length
    onBatchProgress?.(done, total)
  }

  return uploaded
}

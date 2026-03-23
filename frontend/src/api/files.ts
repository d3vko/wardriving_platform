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

export function getDeviceSources(): Promise<DeviceSourcesResponse> {
  return apiFetch<DeviceSourcesResponse>('/device-sources/', { skipAuth: true })
}

export function uploadFiles(
  files: File[],
  deviceSource: string,
): Promise<FileUploaded[]> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('device_source', deviceSource)

  return apiFetch<FileUploaded[]>('/files-uploaded/', {
    method: 'POST',
    body: form,
  })
}

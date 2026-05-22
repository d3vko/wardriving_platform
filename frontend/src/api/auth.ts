import { apiFetch } from './client'

export interface LoginResponse {
  access: string
  refresh: string
  username: string
}

export interface RegisterResponse {
  user: {
    id: number
    username: string
    email: string
  }
  tokens: {
    access: string
    refresh: string
  }
}

export interface RefreshResponse {
  access: string
}

export function login(username: string, password: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
    skipAuth: true,
  })
}

export function register(
  username: string,
  email: string,
  password: string,
  passwordConfirm: string,
): Promise<RegisterResponse> {
  return apiFetch<RegisterResponse>('/auth/register/', {
    method: 'POST',
    body: JSON.stringify({ username, email, password, password_confirm: passwordConfirm }),
    skipAuth: true,
  })
}

export function refreshToken(refresh: string): Promise<RefreshResponse> {
  return apiFetch<RefreshResponse>('/auth/token/refresh/', {
    method: 'POST',
    body: JSON.stringify({ refresh }),
    skipAuth: true,
  })
}

export function requestPasswordReset(email: string): Promise<{ detail: string }> {
  return apiFetch<{ detail: string }>('/auth/password/reset/', {
    method: 'POST',
    body: JSON.stringify({ email }),
    skipAuth: true,
  })
}

export function confirmPasswordReset(
  uid: string,
  token: string,
  new_password: string,
  new_password_confirm: string,
): Promise<{ detail: string }> {
  return apiFetch<{ detail: string }>('/auth/password/reset/confirm/', {
    method: 'POST',
    body: JSON.stringify({ uid, token, new_password, new_password_confirm }),
    skipAuth: true,
  })
}

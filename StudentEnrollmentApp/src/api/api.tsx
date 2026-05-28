import {
  AxiosError,
  AxiosResponse,
  InternalAxiosRequestConfig,
  create,
} from 'axios';
import { Platform } from 'react-native';
import { tokenStorage } from './storage';

// -------------------
// Base URL
// -------------------
const DEPLOYED_API_URL = 'https://enrollmentsystem-uuds.onrender.com/api/';
const LAN_API_URL = DEPLOYED_API_URL;
const WEB_API_URL = DEPLOYED_API_URL;
const ANDROID_EMULATOR_API_URL = 'http://10.0.2.2:8000/api/';

const getApiBaseUrl = () => {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }

  if (Platform.OS === 'web') {
    return WEB_API_URL;
  }

  if (
    Platform.OS === 'android' &&
    process.env.EXPO_PUBLIC_ANDROID_EMULATOR === 'true'
  ) {
    return ANDROID_EMULATOR_API_URL;
  }

  return LAN_API_URL;
};

export const API_BASE_URL = getApiBaseUrl();

export const getChatbotWebSocketUrl = (token: string) => {
  const websocketUrl = new URL(
    process.env.EXPO_PUBLIC_CHATBOT_WS_URL || API_BASE_URL
  );

  websocketUrl.protocol = websocketUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  websocketUrl.pathname = websocketUrl.pathname
    .replace(/\/api\/?$/, '')
    .replace(/\/$/, '');
  websocketUrl.pathname = `${websocketUrl.pathname}/ws/chatbot/`;
  websocketUrl.searchParams.set('token', token);

  return websocketUrl.toString();
};

export const api = create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

interface RetriableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

api.interceptors.request.use(async (config) => {
  const token = await tokenStorage.getItem('accessToken');

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableRequestConfig | undefined;
    const isLoginRequest = originalRequest?.url?.includes('auth/login/');
    const isRefreshRequest = originalRequest?.url?.includes('auth/token/refresh/');

    if (
      error?.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isLoginRequest &&
      !isRefreshRequest
    ) {
      const refreshToken = await tokenStorage.getItem('refreshToken');

      if (refreshToken) {
        try {
          originalRequest._retry = true;

          const refreshResponse = await api.post('auth/token/refresh/', {
            refresh: refreshToken,
          });

          const newAccessToken = refreshResponse.data?.access;

          if (newAccessToken) {
            await tokenStorage.setItem('accessToken', newAccessToken);
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            return api(originalRequest);
          }
        } catch {
          await tokenStorage.removeAuthTokens();
        }
      } else {
        await tokenStorage.removeAuthTokens();
      }
    } else if (error?.response?.status === 401 && !isLoginRequest) {
      await tokenStorage.removeAuthTokens();
    }

    return Promise.reject(error);
  }
);

// -------------------
// Interfaces
// -------------------
export interface RegisterData {
  email: string;
  password: string;
  first_name: string;
  middle_name?: string;
  last_name: string;
  student_number: string;
  parent_name?: string;
  contact_number?: string;
  home_address?: string;
  birthday?: string | null;
  course: string;
  year_level: string;
  semester: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
}

// -------------------
// Auth API
// -------------------
export const registerStudent = (data: RegisterData) =>
  api.post('auth/register/', data);

export const loginStudent = (data: LoginData) =>
  api.post<LoginResponse>('auth/login/', data);

export const verifyAccount = (data: { email: string; code: string }) =>
  api.post('auth/verify/', data);

export const resendActivationCode = (data: { email: string }) =>
  api.post('auth/resend-code/', data);

export function getListData<T>(data: T[] | { results?: T[] }): T[] {
  if (Array.isArray(data)) {
    return data;
  }

  return Array.isArray(data?.results) ? data.results : [];
}

interface PaginatedResponse<T> {
  next?: string | null;
  results?: T[];
}

export async function getAllPages<T>(
  url: string,
  config?: Parameters<typeof api.get>[1]
): Promise<T[]> {
  const allItems: T[] = [];
  let nextUrl: string | null = url;
  let requestConfig = config;

  while (nextUrl) {
    const response: AxiosResponse<T[] | PaginatedResponse<T>> =
      await api.get<T[] | PaginatedResponse<T>>(
      nextUrl,
      requestConfig
    );

    if (Array.isArray(response.data)) {
      return [...allItems, ...response.data];
    }

    allItems.push(...getListData<T>(response.data));
    nextUrl = response.data.next || null;
    requestConfig = undefined;
  }

  return allItems;
}

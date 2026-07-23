// src/config/index.ts

export const config = {
  apiUrl: import.meta.env.VITE_API_URL,
  wsUrl: import.meta.env.VITE_WS_URL,
  imageBaseUrl: import.meta.env.VITE_IMAGE_BASE_URL,
} as const;
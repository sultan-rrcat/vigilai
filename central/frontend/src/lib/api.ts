// src/lib/api.ts
import axios from 'axios';
import type { Camera, Incident } from '../types';
import { config } from '../config/index';


const API_BASE_URL = config.apiUrl;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Incident endpoints
  getIncidents: async (status = 'active, escalated') => {
    const res = await apiClient.get<Incident[]>(`/incidents/?status=${status}`);
    return res.data;
  },
  acknowledgeIncident: async (id: string) => {
    const res = await apiClient.post(`/incidents/${id}/acknowledge`);
    return res.data;
  },

  // Camera & Zone endpoints
  getCameras: async () => {
    const res = await apiClient.get<Camera[]>('/cameras');
    return res.data;
  },

  addCamera: async (data: { name: string; location: string; rtsp_url: string }) => {
    // Sends the new camera data to the backend
    const res = await apiClient.post<Camera>('/cameras', data);
    return res.data;
  },

  deleteCamera: async (cameraId: string) => {
    const res = await apiClient.delete(`/cameras/${cameraId}`);
    return res.data;
  },

  getZones: async (cameraId: string) => {
    const res = await apiClient.get(`/cameras/${cameraId}/zones/`);
    return res.data;
  },

  deleteAllZones: async (cameraId: string) => {
    const res = await apiClient.delete(`/cameras/${cameraId}/zones/`);
    return res.data;
  },

  createZone: async (cameraId: string, name: string, polygon: number[][], minDwell: number = 2.0) => {
    const res = await apiClient.post(`/cameras/${cameraId}/zones/`, {
      name,
      polygon,
      min_dwell_seconds: minDwell
    });
    return res.data;
  },

  getSettings: async () => {
    const res = await apiClient.get('/settings');
    return res.data;
  },
  
  updateSettings: async (data: { escalation_timeout_sec: number, webhook_url: string | null, retention_days: number }) => {
    const res = await apiClient.put('/settings', data);
    return res.data;
  }
};
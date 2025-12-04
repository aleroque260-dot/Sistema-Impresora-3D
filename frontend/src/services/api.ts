import axios from 'axios';

// Configuración base de la API
const API_BASE_URL = 'http://localhost:8000/api';

// Crear instancia de axios
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar token a cada request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para manejar errores y refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Si error es 401 y no es un intento de refresh previo
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          // No hay refresh token, redirigir a login
          window.location.href = '/login';
          return Promise.reject(error);
        }
        
        // Intentar refresh token
        const response = await axios.post(`${API_BASE_URL}/token/refresh/`, {
          refresh: refreshToken,
        });
        
        const { access } = response.data;
        
        // Guardar nuevo token
        localStorage.setItem('access_token', access);
        
        // Actualizar header y reintentar request original
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);
        
      } catch (refreshError) {
        // Error en refresh, limpiar tokens y redirigir
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// Servicios de autenticación
export const authService = {
  login: async (username: string, password: string) => {
    const response = await axios.post(`${API_BASE_URL}/token/`, {
      username,
      password,
    });
    return response.data;
  },
  
  register: async (userData: {
    username: string;
    email: string;
    password: string;
    password2: string;
    first_name?: string;
    last_name?: string;
  }) => {
    const response = await axios.post(`${API_BASE_URL}/auth/register/`, userData);
    return response.data;
  },
  
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
  
  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },
};

// Servicios de la API
export const printerService = {
  getAll: () => api.get('/printers/'),
  getById: (id: number) => api.get(`/printers/${id}/`),
  create: (data: any) => api.post('/printers/', data),
  update: (id: number, data: any) => api.put(`/printers/${id}/`, data),
  delete: (id: number) => api.delete(`/printers/${id}/`),
};

export const departmentService = {
  getAll: () => api.get('/departments/'),
};

export const printJobService = {
  getAll: () => api.get('/print-jobs/'),
  create: (data: any) => api.post('/print-jobs/', data),
  approve: (id: number) => api.post(`/print-jobs/${id}/approve/`),
  startPrinting: (id: number) => api.post(`/print-jobs/${id}/start_printing/`),
  complete: (id: number, actualHours: number) => 
    api.post(`/print-jobs/${id}/complete/`, { actual_hours: actualHours }),
};

export const userService = {
  getProfile: () => api.get('/users/me/'),
  updateProfile: (data: any) => api.put('/users/me/', data),
};

export const dashboardService = {
  getStats: () => api.get('/dashboard/stats/'),
};

export default api;
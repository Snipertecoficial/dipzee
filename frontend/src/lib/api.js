import axios from 'axios';
import { getAccessToken, setAccessToken } from './session';

export { setAccessToken } from './session';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Access tokens are short-lived on purpose (see backend/security.py); this
// transparently exchanges an expired one for a new one via the refresh
// token and retries the original request once. Concurrent 401s share a
// single in-flight refresh call instead of each triggering their own.
let refreshPromise = null;

async function refreshAccessToken() {
  const { data } = await axios.post(`${API}/auth/refresh`, null, { withCredentials: true });
  setAccessToken(data.access_token);
  return data.access_token;
}

function clearSessionAndRedirect() {
  setAccessToken(null);
  if (window.location.pathname.startsWith('/app')) {
    window.location.href = '/login';
  }
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const isAuthRoute = original?.url?.includes('/auth/login')
      || original?.url?.includes('/auth/register')
      || original?.url?.includes('/auth/refresh');

    if (status === 401 && original && !original._retried && !isAuthRoute) {
      original._retried = true;
      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => { refreshPromise = null; });
        }
        const newToken = await refreshPromise;
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      } catch (refreshError) {
        clearSessionAndRedirect();
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);

export default api;

import axios from 'axios'

const api = axios.create({ baseURL: '/api/', timeout: 300000 })
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401 && error.response?.data?.detail === 'PIN_REQUIRED') {
      window.dispatchEvent(new Event('athan-pin-required'))
    }
    return Promise.reject(error)
  }
)

export default api


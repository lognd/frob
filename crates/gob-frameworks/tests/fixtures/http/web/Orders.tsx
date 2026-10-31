import axios from 'axios';
import * as kk from 'ky';

export function Orders({ id, base }: { id: string; base: string }) {
  const create = () => fetch('/api/orders', { method: 'POST' });
  const one = () => fetch(`/api/orders/${id}`);
  const opaque = () => fetch(base);
  const viaAxios = () => axios.get('/api/items');
  const viaKy = () => kk.delete('/api/items/7');
  const cfg = () => axios({ url: '/api/items', method: 'put', baseURL: base });
  return null;
}

export function shadow() {
  function fetch(u: string) { return u; }
  return fetch('/api/orders');
}

import { Injectable } from '@angular/core';
import { jwtDecode } from 'jwt-decode';

const KB_TOKEN_KEY = 'kb_access_token';

interface JwtPayload {
  roles?: string[];
  groups?: string[];
}

const KB_STAFF_ROLES = new Set([
  'level1_agent',
  'level2_agent',
  'agent',
  'manager',
  'admin',
]);

@Injectable({ providedIn: 'root' })
export class AuthService {
  getToken(): string | null {
    return sessionStorage.getItem(KB_TOKEN_KEY);
  }

  setToken(token: string): void {
    sessionStorage.setItem(KB_TOKEN_KEY, token.trim());
  }

  clearToken(): void {
    sessionStorage.removeItem(KB_TOKEN_KEY);
  }

  isKbStaff(): boolean {
    const t = this.getToken();
    if (!t) return false;
    try {
      const p = jwtDecode<JwtPayload>(t);
      const raw = [...(p.roles ?? []), ...(p.groups ?? [])];
      const roles = raw.map((r) => r.toLowerCase());
      return roles.some((r) => KB_STAFF_ROLES.has(r));
    } catch {
      return false;
    }
  }
}

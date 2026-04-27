import { useSyncExternalStore } from "react";

import { findRoleRouteByRole, type UserRole } from "./role-routes";

const STORAGE_KEY = "trms.mock-role";
const listeners = new Set<() => void>();
const memoryStorage = new Map<string, string>();

export type AuthSession = {
  role: UserRole;
  displayName: string;
  memberCode: string | null;
};

function isUserRole(value: unknown): value is UserRole {
  return value === "member" || value === "admin" || value === "system_admin";
}

function getRoleRouteOrThrow(role: UserRole) {
  const roleRoute = findRoleRouteByRole(role);
  if (!roleRoute) {
    throw new Error(`Unknown role route: ${role}`);
  }
  return roleRoute;
}

function createSession(role: UserRole): AuthSession {
  const roleRoute = getRoleRouteOrThrow(role);
  return {
    role,
    displayName: roleRoute.mockDisplayName,
    memberCode: roleRoute.mockMemberCode,
  };
}

function readPersistedRole() {
  if (typeof window !== "undefined") {
    const storage = window.localStorage;
    if (storage && typeof storage.getItem === "function") {
      try {
        return storage.getItem(STORAGE_KEY);
      } catch {
        return memoryStorage.get(STORAGE_KEY) ?? null;
      }
    }
  }

  return memoryStorage.get(STORAGE_KEY) ?? null;
}

function persistRole(role: UserRole | null) {
  if (typeof window !== "undefined") {
    const storage = window.localStorage;
    if (
      storage
      && typeof storage.setItem === "function"
      && typeof storage.removeItem === "function"
    ) {
      try {
        if (role) {
          storage.setItem(STORAGE_KEY, role);
        } else {
          storage.removeItem(STORAGE_KEY);
        }
        return;
      } catch {
        // Fall back to in-memory storage in nonstandard test environments.
      }
    }
  }

  if (role) {
    memoryStorage.set(STORAGE_KEY, role);
  } else {
    memoryStorage.delete(STORAGE_KEY);
  }
}

function readStoredRole(): UserRole | null {
  const rawRole = readPersistedRole();
  return isUserRole(rawRole) ? rawRole : null;
}

const initialRole = readStoredRole();
let currentSession = initialRole ? createSession(initialRole) : null;

function emitChange() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot() {
  return currentSession;
}

export function buildLoginPath(nextPath?: string) {
  if (!nextPath) {
    return "/login";
  }

  const searchParams = new URLSearchParams({
    next: nextPath,
  });
  return `/login?${searchParams.toString()}`;
}

export function setMockSession(role: UserRole) {
  currentSession = createSession(role);
  persistRole(role);
  emitChange();
}

export function clearMockSession() {
  currentSession = null;
  persistRole(null);
  emitChange();
}

export function useAuthSession() {
  return useSyncExternalStore(subscribe, getSnapshot, () => null);
}

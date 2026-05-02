import { useSyncExternalStore } from "react";

import { setApiAccessTokenProvider } from "../lib/api/client";
import { trmsApi } from "../lib/api/trms";
import type { AuthSessionResponse } from "../lib/api/types";
import { findRoleRouteByRole, type UserRole } from "./role-routes";

const STORAGE_KEY = "trms.mock-role";
const SESSION_STORAGE_KEY = "trms.auth-session";
const listeners = new Set<() => void>();
const memoryStorage = new Map<string, string>();

export type AuthSession = {
  role: UserRole;
  availableRoles: UserRole[];
  actorId: string;
  displayName: string;
  memberCode: string | null;
  username: string | null;
  accessToken: string | null;
  isMock: boolean;
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

function normalizeAvailableRoles(
  roles: UserRole[] | undefined,
  fallbackRole: UserRole,
) {
  const normalizedRoles = (roles ?? []).filter((role, index, items) => (
    isUserRole(role) && items.indexOf(role) === index
  ));
  if (normalizedRoles.length > 0) {
    return normalizedRoles;
  }
  return [fallbackRole];
}

function createSession(
  role: UserRole,
  availableRoles?: UserRole[],
  overrides?: Partial<Omit<AuthSession, "role" | "availableRoles" | "isMock">>,
): AuthSession {
  const roleRoute = getRoleRouteOrThrow(role);
  const normalizedAvailableRoles = normalizeAvailableRoles(availableRoles, role);
  return {
    role,
    availableRoles: normalizedAvailableRoles,
    actorId: overrides?.actorId ?? roleRoute.mockActorId,
    displayName: overrides?.displayName ?? roleRoute.mockDisplayName,
    memberCode: overrides?.memberCode ?? roleRoute.mockMemberCode,
    username: overrides?.username ?? null,
    accessToken: overrides?.accessToken ?? null,
    isMock: true,
  };
}

function readPersistedItem(storageKey: string) {
  if (typeof window !== "undefined") {
    const storage = window.localStorage;
    if (storage && typeof storage.getItem === "function") {
      try {
        return storage.getItem(storageKey);
      } catch {
        return memoryStorage.get(storageKey) ?? null;
      }
    }
  }

  return memoryStorage.get(storageKey) ?? null;
}

function persistItem(storageKey: string, value: string | null) {
  if (typeof window !== "undefined") {
    const storage = window.localStorage;
    if (
      storage
      && typeof storage.setItem === "function"
      && typeof storage.removeItem === "function"
    ) {
      try {
        if (value) {
          storage.setItem(storageKey, value);
        } else {
          storage.removeItem(storageKey);
        }
        return;
      } catch {
        // Fall back to in-memory storage in nonstandard test environments.
      }
    }
  }

  if (value) {
    memoryStorage.set(storageKey, value);
  } else {
    memoryStorage.delete(storageKey);
  }
}

function readStoredRole(): UserRole | null {
  const rawRole = readPersistedItem(STORAGE_KEY);
  return isUserRole(rawRole) ? rawRole : null;
}

function persistRole(role: UserRole | null) {
  persistItem(STORAGE_KEY, role);
}

function createSessionFromAuthResponse(response: AuthSessionResponse): AuthSession {
  const availableRoles = normalizeAvailableRoles(response.user.roles, response.user.role);
  return {
    role: response.user.role,
    availableRoles,
    actorId: response.user.actor_id,
    displayName: response.user.display_name,
    memberCode: response.user.member_code,
    username: response.user.username,
    accessToken: response.access_token,
    isMock: false,
  };
}

function readStoredSession(): AuthSession | null {
  const rawSession = readPersistedItem(SESSION_STORAGE_KEY);
  if (!rawSession) {
    const legacyRole = readStoredRole();
    return legacyRole ? createSession(legacyRole) : null;
  }

  try {
    const parsed = JSON.parse(rawSession) as Partial<AuthSession>;
    if (
      isUserRole(parsed.role)
      && typeof parsed.actorId === "string"
      && typeof parsed.displayName === "string"
      && (typeof parsed.accessToken === "string" || parsed.accessToken === null)
    ) {
      return {
        role: parsed.role,
        availableRoles: normalizeAvailableRoles(
          Array.isArray(parsed.availableRoles)
            ? parsed.availableRoles.filter(isUserRole)
            : undefined,
          parsed.role,
        ),
        actorId: parsed.actorId,
        displayName: parsed.displayName,
        memberCode: typeof parsed.memberCode === "string" ? parsed.memberCode : null,
        username: typeof parsed.username === "string" ? parsed.username : null,
        accessToken: typeof parsed.accessToken === "string" ? parsed.accessToken : null,
        isMock: Boolean(parsed.isMock),
      };
    }
  } catch {
    // Invalid persisted sessions are discarded instead of being treated as login.
  }

  persistItem(SESSION_STORAGE_KEY, null);
  return null;
}

function persistSession(session: AuthSession | null) {
  persistRole(null);
  persistItem(SESSION_STORAGE_KEY, session ? JSON.stringify(session) : null);
}

let currentSession = readStoredSession();
setApiAccessTokenProvider(() => currentSession?.accessToken ?? null);

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

export function setMockSession(
  role: UserRole,
  availableRolesOrOverrides?: UserRole[] | Partial<Omit<AuthSession, "role" | "availableRoles" | "isMock">>,
  overrides?: Partial<Omit<AuthSession, "role" | "availableRoles" | "isMock">>,
) {
  const availableRoles = Array.isArray(availableRolesOrOverrides) ? availableRolesOrOverrides : undefined;
  const resolvedOverrides = Array.isArray(availableRolesOrOverrides) ? overrides : availableRolesOrOverrides;
  currentSession = createSession(role, availableRoles, resolvedOverrides);
  persistSession(currentSession);
  emitChange();
}

export function clearMockSession() {
  currentSession = null;
  persistSession(null);
  emitChange();
}

export async function registerWithPassword(payload: {
  username: string;
  password: string;
  role: UserRole;
  displayName?: string;
  actorId?: string;
  memberCode?: string;
}) {
  const response = await trmsApi.register({
    username: payload.username,
    password: payload.password,
    role: payload.role,
    display_name: payload.displayName || null,
    actor_id: payload.actorId || null,
    member_code: payload.memberCode || null,
  });
  currentSession = createSessionFromAuthResponse(response);
  persistSession(currentSession);
  emitChange();
  return currentSession;
}

export async function loginWithPassword(payload: { username: string; password: string }) {
  const response = await trmsApi.login(payload);
  currentSession = createSessionFromAuthResponse(response);
  persistSession(currentSession);
  emitChange();
  return currentSession;
}

export async function switchCurrentRole(role: UserRole) {
  if (!currentSession || currentSession.role === role) {
    return currentSession;
  }
  if (!currentSession.availableRoles.includes(role)) {
    throw new Error(`Current account cannot switch to role '${role}'`);
  }

  if (currentSession.isMock || !currentSession.accessToken) {
    const roleRoute = getRoleRouteOrThrow(role);
    currentSession = {
      ...currentSession,
      role,
      actorId: roleRoute.mockActorId,
      displayName: roleRoute.mockDisplayName,
      memberCode: roleRoute.mockMemberCode,
    };
    persistSession(currentSession);
    emitChange();
    return currentSession;
  }

  const response = await trmsApi.switchRole(currentSession.accessToken, { role });
  currentSession = createSessionFromAuthResponse(response);
  persistSession(currentSession);
  emitChange();
  return currentSession;
}

export async function logoutCurrentSession() {
  const accessToken = currentSession?.accessToken ?? null;
  currentSession = null;
  persistSession(null);
  emitChange();
  if (accessToken) {
    await trmsApi.logout(accessToken);
  }
}

export function useAuthSession() {
  return useSyncExternalStore(subscribe, getSnapshot, () => null);
}

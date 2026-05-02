"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "@/lib/api";
import {
  clearToken, getStoredUser, getToken, setStoredUser, setToken,
} from "@/lib/auth";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]     = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = getStoredUser();
    if (stored && getToken()) {
      setUser(stored as unknown as User);
    }
    setLoading(false);
  }, []);

  async function login(email: string, password: string) {
    const res = await api.post<{
      access_token: string; user_id: number; role: string; full_name?: string;
    }>("/api/v1/auth/login", { email, password });

    setToken(res.access_token);
    const me = await api.get<User>("/api/v1/auth/me");
    setStoredUser(me as unknown as Record<string, unknown>);
    setUser(me);
  }

  function logout() {
    clearToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

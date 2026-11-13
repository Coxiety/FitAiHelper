import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/lib/auth";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  hasHydrated: boolean;
  setAuth: (user: User, token: string) => void;
  setHasHydrated: (state: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      hasHydrated: false,

      setAuth: (user, token) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", token);
        }
        set({ user, token, isAuthenticated: true, hasHydrated: true });
      },

      setHasHydrated: (state) => {
        const rawToken =
          typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
        if (rawToken) {
          set({ hasHydrated: state, token: rawToken, isAuthenticated: true });
        } else {
          set({ hasHydrated: state, isAuthenticated: false, token: null, user: null });
        }
      },

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
        }
        set({ user: null, token: null, isAuthenticated: false, hasHydrated: true });
      },
    }),
    {
      name: "fitai-auth",
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

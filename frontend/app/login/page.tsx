"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const router    = useRouter();
  const [email, setEmail]       = useState("admin@c2d2.local");
  const [password, setPassword] = useState("changeme123");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0d1117]">
      <div className="w-full max-w-md px-6">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-black text-white tracking-tight">C2D2</h1>
          <p className="text-[#8b949e] text-sm mt-1 uppercase tracking-widest">
            Collaborative Combat Decision Dominance
          </p>
          <div className="mt-3 flex justify-center gap-3 text-[10px] uppercase tracking-widest">
            <span className="text-[#3fb950]">Train Smarter</span>
            <span className="text-[#8b949e]">·</span>
            <span className="text-[#f59e0b]">Select Better</span>
            <span className="text-[#8b949e]">·</span>
            <span className="text-[#f85149]">Execute Faster</span>
          </div>
        </div>

        {/* Card */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-[#8b949e] mb-1.5 uppercase tracking-wider">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-md text-white text-sm focus:outline-none focus:border-[#f59e0b] transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs text-[#8b949e] mb-1.5 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-md text-white text-sm focus:outline-none focus:border-[#f59e0b] transition-colors"
              />
            </div>
            {error && (
              <p className="text-[#f85149] text-xs">{error}</p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-[#f59e0b] hover:bg-[#d97706] text-black font-bold text-sm rounded-md transition-colors disabled:opacity-50"
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </div>

        <p className="text-center text-[10px] text-[#8b949e] mt-4">
          Default: admin@c2d2.local / changeme123
        </p>
      </div>
    </div>
  );
}

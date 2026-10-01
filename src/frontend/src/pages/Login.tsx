import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ROLE_LABEL, type Role } from "../api";
import { useAuth } from "../auth";
import { Button, ErrorText } from "../components/ui";

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("demo");
  const [err, setErr] = useState<unknown>(null);
  const demo = useQuery({ queryKey: ["demo-users"], queryFn: () => api<{ username: string; name: string; role: Role }[]>("/users/demo") });
  if (user) return <Navigate to="/" replace />;

  const go = async (u: string, p: string) => {
    setErr(null);
    try {
      await login(u, p);
      nav("/");
    } catch (e) {
      setErr(e);
    }
  };

  const groups = (["product_owner", "analyst", "committee"] as Role[]).map((r) => [r, demo.data?.filter((d) => d.role === r) ?? []] as const);

  return (
    <div className="mx-auto mt-16 max-w-3xl px-4">
      <h1 className="text-2xl font-semibold">Risk Assessment Workbench</h1>
      <p className="mt-1 text-sm text-slate-500">
        Financial-crime risk assessment for new products and changes. Synthetic demo data only: every company, person and jurisdiction is fictional.
      </p>
      <div className="mt-8 grid gap-6 md:grid-cols-[1fr_16rem]">
        <div>
          <h2 className="label">Sign in as a demo persona</h2>
          <div className="space-y-4">
            {groups.map(([role, users]) => (
              <div key={role}>
                <p className="mb-1 text-sm font-medium text-slate-700">{ROLE_LABEL[role]}</p>
                <div className="flex flex-wrap gap-2">
                  {users.map((u) => (
                    <Button key={u.username} variant="secondary" data-testid={`persona-${u.username}`} onClick={() => go(u.username, "demo")}>
                      {u.name}
                    </Button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
        <form
          className="rounded-lg border border-slate-200 bg-white p-4"
          onSubmit={(e) => {
            e.preventDefault();
            go(username, password);
          }}
        >
          <label className="label">Username</label>
          <input data-testid="username" className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
          <label className="label mt-3">Password</label>
          <input data-testid="password" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Button className="mt-4 w-full" type="submit" data-testid="login">
            Sign in
          </Button>
          <ErrorText error={err} />
        </form>
      </div>
    </div>
  );
}

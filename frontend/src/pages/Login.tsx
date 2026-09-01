import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ApiError } from "../api/client";
import sotecLogo from "../assets/sotec-logo.png";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("Admin");
  const [password, setPassword] = useState("1234");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "로그인에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <img src={sotecLogo} alt="SOTEC" className="login-logo" />
        <h1>SW 자산 견적서 관리 시스템</h1>
        <p className="muted">1단계 · 견적서 관리 (데모)</p>

        <label>
          아이디
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>
          비밀번호
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        {error && <div className="form-error">{error}</div>}

        <button type="submit" disabled={busy}>
          {busy ? "로그인 중..." : "로그인"}
        </button>

        <div className="login-hint">
          데모 계정 · <code>Admin / 1234</code> (전체관리자) ·{" "}
          <code>test1 / 1234</code> (그룹관리자 A · 조회 전용)
        </div>
      </form>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { api } from "../api";

export function UsernameField({
  value,
  verified = false,
  displayName: savedDisplayName = "",
  platform = "twitch",
  onSave,
}) {
  const [text, setText] = useState(value || "");
  const [status, setStatus] = useState("idle");
  const [displayName, setDisplayName] = useState("");
  const [focused, setFocused] = useState(false);
  const verifySeq = useRef(0);
  const syncedVerifiedRef = useRef(null);

  useEffect(() => {
    setText(value || "");
  }, [value]);

  useEffect(() => {
    const trimmed = text.trim();
    if (!trimmed) {
      setStatus("idle");
      setDisplayName("");
      return undefined;
    }

    setStatus("checking");
    const seq = ++verifySeq.current;
    const timer = window.setTimeout(async () => {
      try {
        const result = await api.verifyUsername(trimmed, platform);
        if (seq !== verifySeq.current) {
          return;
        }

        if (result.error === "invalid_format") {
          setStatus("invalid");
          setDisplayName("");
          return;
        }
        if (result.error === "lookup_failed") {
          setStatus("error");
          setDisplayName("");
          return;
        }
        if (result.found) {
          setStatus("found");
          setDisplayName(result.display_name || result.login || trimmed);
          return;
        }

        setStatus("not_found");
        setDisplayName("");
      } catch {
        if (seq === verifySeq.current) {
          setStatus("error");
          setDisplayName("");
        }
      }
    }, 400);

    return () => window.clearTimeout(timer);
  }, [text, platform]);

  useEffect(() => {
    const trimmed = text.trim();
    if (status !== "found" || !trimmed || trimmed !== (value || "").trim()) {
      return;
    }
    const platformName = displayName.trim();
    if (!platformName) {
      return;
    }
    const needsSync =
      !verified || platformName !== (savedDisplayName || "").trim();
    if (!needsSync) {
      return;
    }
    const syncKey = `${trimmed}:${platformName}`;
    if (syncedVerifiedRef.current === syncKey) {
      return;
    }
    syncedVerifiedRef.current = syncKey;
    onSave(trimmed, true, platformName);
  }, [status, text, value, verified, displayName, savedDisplayName, onSave]);

  useEffect(() => {
    syncedVerifiedRef.current = null;
  }, [value, verified, savedDisplayName]);

  const handleBlur = () => {
    setFocused(false);
    const trimmed = text.trim();
    const isVerified = status === "found";
    const usernameChanged = trimmed !== (value || "").trim();
    const verificationChanged =
      trimmed &&
      ((isVerified && !verified) || (!isVerified && verified) || status === "not_found" || status === "invalid");

    if (usernameChanged || verificationChanged) {
      onSave(trimmed, isVerified, isVerified ? displayName : "");
    }
  };

  const showInvalid = status === "not_found" || status === "invalid";
  let hint = null;
  if (status === "found" && displayName && focused) {
    hint = <span className="username-field__hint status-on">Found: {displayName}</span>;
  } else if (status === "not_found") {
    hint = <span className="username-field__hint status-off">User not found on Twitch</span>;
  } else if (status === "invalid") {
    hint = (
      <span className="username-field__hint status-off">
        Invalid username (4-25 characters, letters, numbers, underscores)
      </span>
    );
  } else if (status === "error") {
    hint = <span className="username-field__hint status-off">Could not verify username right now</span>;
  }

  return (
    <>
      <div className="username-field">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={handleBlur}
          placeholder="Username"
          className={showInvalid ? "username-field__input--invalid" : undefined}
          autoComplete="username"
          spellCheck={false}
        />
        <span className="username-field__status" aria-hidden="true">
          {status === "checking" && (
            <span className="icon username-field__icon username-field__icon--spin">progress_activity</span>
          )}
          {status === "found" && (
            <span className="icon username-field__icon status-on">check_circle</span>
          )}
          {(status === "not_found" || status === "invalid") && (
            <span className="icon username-field__icon status-off">cancel</span>
          )}
          {status === "error" && (
            <span className="icon username-field__icon status-off">error</span>
          )}
        </span>
      </div>
      {hint}
    </>
  );
}

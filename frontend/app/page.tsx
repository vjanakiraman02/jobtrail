"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  API_BASE,
  STATUSES,
  api,
  type Application,
  type ExtractedJob,
  type Status,
} from "../lib/api";

const MIN_POSTING_CHARS = 20; // matches the API's minimum

type Filter = Status | "all";

const EMPTY_FORM = { company: "", title: "", location: "", url: "" };

export default function Home() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [posting, setPosting] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [extracted, setExtracted] = useState<ExtractedJob | null>(null);
  const [extractError, setExtractError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setApplications(await api.list());
      setError(null);
    } catch {
      setError(`Could not reach the API at ${API_BASE}. Is the backend running?`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = useMemo(() => {
    const result: Record<string, number> = { all: applications.length };
    for (const status of STATUSES) result[status] = 0;
    for (const application of applications) result[application.status] += 1;
    return result;
  }, [applications]);

  const visible = useMemo(
    () => (filter === "all" ? applications : applications.filter((a) => a.status === filter)),
    [applications, filter],
  );

  async function handleAdd() {
    setSaving(true);
    try {
      const created = await api.create({
        company: form.company.trim(),
        title: form.title.trim(),
        location: form.location.trim() || undefined,
        url: form.url.trim() || undefined,
        // Keep the pasted posting so it is still there once it disappears from the web.
        description: posting.trim() || undefined,
      });
      setApplications((current) => [created, ...current]);
      setForm(EMPTY_FORM);
      setPosting("");
      setExtracted(null);
      setExtractError(null);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the application.");
    } finally {
      setSaving(false);
    }
  }

  async function handleExtract() {
    setExtracting(true);
    setExtractError(null);
    try {
      const job = await api.extract(posting.trim());
      setExtracted(job);
      // Only fill what the model found; anything it left out stays as typed.
      setForm((current) => ({
        ...current,
        company: job.company ?? current.company,
        title: job.title ?? current.title,
        location: job.location ?? current.location,
      }));
    } catch (e) {
      setExtracted(null);
      setExtractError(
        e instanceof TypeError
          ? `Could not reach the API at ${API_BASE}. Is the backend running?`
          : e instanceof Error
            ? e.message
            : "Extraction failed.",
      );
    } finally {
      setExtracting(false);
    }
  }

  async function handleStatus(id: number, status: Status) {
    try {
      const updated = await api.update(id, { status });
      setApplications((current) => current.map((a) => (a.id === id ? updated : a)));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update the status.");
    }
  }

  async function handleDelete(id: number) {
    try {
      await api.remove(id);
      setApplications((current) => current.filter((a) => a.id !== id));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete the application.");
    }
  }

  return (
    <main className="page">
      <header className="header">
        <h1>JobTrail</h1>
        <p className="sub">Every application, from first save to final offer.</p>
      </header>

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      <section className="card" aria-labelledby="add-heading">
        <h2 id="add-heading">Add an application</h2>

        <div className="extract">
          <label htmlFor="posting">
            Paste a job posting to fill in the form (optional)
          </label>
          <textarea
            id="posting"
            rows={5}
            placeholder="Paste the full job description here…"
            value={posting}
            onChange={(e) => setPosting(e.target.value)}
          />
          <div className="extract-actions">
            <button
              type="button"
              className="secondary"
              disabled={extracting || posting.trim().length < MIN_POSTING_CHARS}
              onClick={() => void handleExtract()}
            >
              {extracting ? "Reading posting…" : "Fill from posting"}
            </button>
            <span className="hint">
              The text goes to the model set in your .env. With Ollama it stays on your computer.
            </span>
          </div>
          {extractError && (
            <p role="alert" className="error small">
              {extractError}
            </p>
          )}
          {extracted && (
            <div className="review" aria-live="polite">
              <p className="hint">Filled from the posting. Check every field before adding.</p>
              <p className="muted small">
                {[extracted.work_mode, extracted.salary_range].filter(Boolean).join(" · ") ||
                  "No work mode or pay stated"}
              </p>
              {extracted.required_skills.length > 0 && (
                <ul className="tags" aria-label="Skills mentioned in the posting">
                  {extracted.required_skills.map((skill) => (
                    <li key={skill} className="tag">
                      {skill}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            void handleAdd();
          }}
        >
          <label>
            Company
            <input
              required
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
            />
          </label>
          <label>
            Job title
            <input
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </label>
          <label>
            Location
            <input
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
            />
          </label>
          <label>
            Posting link
            <input
              type="url"
              placeholder="https://"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
            />
          </label>
          <button type="submit" className="primary" disabled={saving}>
            {saving ? "Saving…" : "Add"}
          </button>
        </form>
      </section>

      <nav className="filters" aria-label="Filter by status">
        {(["all", ...STATUSES] as const).map((value) => (
          <button
            key={value}
            type="button"
            className="chip"
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {value} <span className="count">{counts[value]}</span>
          </button>
        ))}
      </nav>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : visible.length === 0 ? (
        <p className="muted">
          {applications.length === 0
            ? "No applications yet. Add your first one above."
            : "Nothing with that status yet."}
        </p>
      ) : (
        <ul className="list">
          {visible.map((application) => (
            <li key={application.id} className="item">
              <div className="item-main">
                <h3>
                  {application.url ? (
                    <a href={application.url} target="_blank" rel="noopener noreferrer">
                      {application.title}
                    </a>
                  ) : (
                    application.title
                  )}
                </h3>
                <p className="muted">
                  {application.company}
                  {application.location ? ` · ${application.location}` : ""}
                </p>
              </div>
              <div className="item-actions">
                <select
                  aria-label={`Status for ${application.title} at ${application.company}`}
                  className="badge"
                  data-status={application.status}
                  value={application.status}
                  onChange={(e) => void handleStatus(application.id, e.target.value as Status)}
                >
                  {STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => void handleDelete(application.id)}
                  aria-label={`Delete ${application.title} at ${application.company}`}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

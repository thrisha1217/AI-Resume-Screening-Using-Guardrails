import { useState } from 'react';
import { ScreeningResults, Candidate } from '../types';
import { getDownloadUrl } from '../api';

interface Props {
  results: ScreeningResults;
  jobId: string;
  onReset: () => void;
}

type Tab = 'in' | 'out' | 'manual' | 'guardrails';

export default function ResultsPage({ results, jobId, onReset }: Props) {
  const [tab, setTab] = useState<Tab>('in');
  const [selected, setSelected] = useState<Candidate | null>(null);

  const inList     = results.results.filter(r => r.status === 'screened in');
  const outList    = results.results.filter(r => r.status === 'screened out');
  const manualList = results.results.filter(r => r.status === 'manual check');

  return (
    <div className="results-page">
      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="summary-card green">
          <div className="summary-num">{results.screened_in}</div>
          <div className="summary-label">Screened In</div>
          <div className="summary-sub">Eligible candidates</div>
        </div>
        <div className="summary-card red">
          <div className="summary-num">{results.screened_out}</div>
          <div className="summary-label">Screened Out</div>
          <div className="summary-sub">Did not meet criteria</div>
        </div>
        <div className="summary-card amber">
          <div className="summary-num">{results.manual_check}</div>
          <div className="summary-label">Manual Check</div>
          <div className="summary-sub">Needs HR review</div>
        </div>
        <div className="summary-card dark">
          <div className="summary-num">{results.total}</div>
          <div className="summary-label">Total</div>
          <div className="summary-sub">Candidates processed</div>
        </div>
      </div>

      {/* Actions */}
      <div className="results-actions">
        <a className="download-btn" href={getDownloadUrl(jobId)} download="screening_results.zip">
          &#11015;&#65039;&nbsp; Download Results (ZIP)
        </a>
        <button className="reset-btn" onClick={onReset}>&#8617; New Screening</button>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button className={`tab ${tab === 'in' ? 'active' : ''}`} onClick={() => setTab('in')}>
          &#9989; Screened In ({results.screened_in})
        </button>
        <button className={`tab ${tab === 'out' ? 'active' : ''}`} onClick={() => setTab('out')}>
          &#10060; Screened Out ({results.screened_out})
        </button>
        <button className={`tab ${tab === 'manual' ? 'active' : ''}`} onClick={() => setTab('manual')}>
          &#9888;&#65039; Manual Check ({results.manual_check})
        </button>
        <button className={`tab ${tab === 'guardrails' ? 'active' : ''}`} onClick={() => setTab('guardrails')}>
          &#128737;&#65039; Guardrails Report
        </button>
      </div>

      <div className="tab-panel">
        {tab === 'guardrails' ? (
          <GuardrailsPanel log={results.guardrails_log} candidates={results.results} />
        ) : (
          <CandidateTable
            candidates={tab === 'in' ? inList : tab === 'out' ? outList : manualList}
            onSelect={setSelected}
            selected={selected}
          />
        )}
      </div>

      {selected && <CandidateModal candidate={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function CandidateTable({ candidates, onSelect, selected }: {
  candidates: Candidate[];
  onSelect: (c: Candidate) => void;
  selected: Candidate | null;
}) {
  if (!candidates.length) return <div className="empty-state">No candidates in this category.</div>;
  return (
    <div className="candidate-table-wrap">
      <table className="candidate-table">
        <thead>
          <tr>
            <th>Applicant ID</th>
            <th>Name</th>
            <th>Degree</th>
            <th>Specialisation</th>
            <th>%</th>
            <th>Exp (yrs)</th>
            <th>Organization</th>
            <th>Reason</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {candidates.map(c => (
            <tr key={c.applicant_id} className={selected?.applicant_id === c.applicant_id ? 'selected-row' : ''}>
              <td className="mono">{c.applicant_id}</td>
              <td className="bold">{c.name}</td>
              <td>{c.degree}</td>
              <td>{c.specialisation}</td>
              <td>{c.percentage}%</td>
              <td>{c.experience_years}</td>
              <td>{c.organization || '—'}</td>
              <td className="reason-cell">{c.reason}</td>
              <td><button className="view-btn" onClick={() => onSelect(c)}>View</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CandidateModal({ candidate: c, onClose }: { candidate: Candidate; onClose: () => void }) {
  const statusColor = c.status === 'screened in' ? '#065F46' : c.status === 'screened out' ? '#991B1B' : '#92400E';
  const statusBg    = c.status === 'screened in' ? '#D1FAE5' : c.status === 'screened out' ? '#FEE2E2' : '#FEF3C7';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-name">{c.name}</div>
            <div className="modal-id">ID: {c.applicant_id}</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="status-badge" style={{ background: statusBg, color: statusColor }}>
              {c.status.toUpperCase()}
            </span>
            <button className="modal-close" onClick={onClose}>&#10005;</button>
          </div>
        </div>

        <div className="modal-body">
          <div className="modal-grid">
            <div className="modal-field"><span className="field-label">Degree</span>{c.degree}</div>
            <div className="modal-field"><span className="field-label">Specialisation</span>{c.specialisation}</div>
            <div className="modal-field"><span className="field-label">Percentage</span>{c.percentage}%</div>
            <div className="modal-field"><span className="field-label">Experience</span>{c.experience_years} years</div>
            <div className="modal-field"><span className="field-label">Organization</span>{c.organization || '—'}</div>
            <div className="modal-field"><span className="field-label">Skills</span><span style={{fontSize:'0.82rem'}}>{c.skills}</span></div>
          </div>

          <div className="modal-section">
            <div className="modal-section-title">&#128203; Screening Reason</div>
            <div className="modal-reason">{c.reason}</div>
          </div>

          {c.resume_summary && c.resume_summary !== 'No resume found.' && (
            <div className="modal-section">
              <div className="modal-section-title">&#128196; Resume Summary</div>
              <div className="modal-reason">{c.resume_summary}</div>
            </div>
          )}

          {c.introduction && (
            <div className="modal-section">
              <div className="modal-section-title">&#129302; AI-Generated Introduction</div>
              <div className="modal-intro">{c.introduction}</div>
            </div>
          )}

          {c.guardrails.length > 0 && (
            <div className="modal-section">
              <div className="modal-section-title">&#128737; Guardrails Applied</div>
              <div className="guardrails-list">
                {c.guardrails.map((g, i) => {
                  const passed  = g.toLowerCase().includes('passed') || g.toLowerCase().includes('checked');
                  const blocked = g.toLowerCase().includes('blocked') || g.toLowerCase().includes('triggered');
                  return (
                    <div key={i} className={`guardrail-item ${blocked ? 'blocked' : passed ? 'passed' : ''}`}>
                      {blocked ? '&#128308;' : passed ? '&#128994;' : '&#128993;'} {g}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function GuardrailsPanel({ log, candidates }: { log: string[]; candidates: Candidate[] }) {
  return (
    <div className="guardrails-panel">
      <div>
        <h3>&#128737; Guardrails Used in This Screening</h3>
        <div className="guardrails-table-wrap">
          <table className="guardrails-table">
            <thead>
              <tr><th>Validator</th><th>What it checks</th><th>Where applied</th><th>Action if triggered</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>ToxicLanguage</strong></td>
                <td>Hate speech, offensive or harmful language</td>
                <td>Degree extraction output, Candidate introductions</td>
                <td>Output rejected, candidate flagged for manual check</td>
              </tr>
              <tr>
                <td><strong>NSFWText</strong></td>
                <td>Sexually explicit or inappropriate content</td>
                <td>Degree extraction output, Candidate introductions</td>
                <td>Output rejected</td>
              </tr>
              <tr>
                <td><strong>GuardrailsPII</strong></td>
                <td>Phone numbers, email addresses in outputs</td>
                <td>Candidate profile text before PDF generation</td>
                <td>PII automatically removed (on_fail="fix")</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3>&#128221; Activity Log</h3>
        <div className="guardrails-list">
          {log.length === 0 ? (
            <div className="guardrail-item passed">
              &#128994; All LLM outputs passed guardrails validation — no toxic, NSFW, or PII content detected.
            </div>
          ) : log.map((entry, i) => (
            <div key={i} className="guardrail-item blocked">&#128308; {entry}</div>
          ))}
        </div>
      </div>

      <div>
        <h3>&#128101; Per-Candidate Guardrails Summary</h3>
        <div className="candidate-table-wrap">
          <table className="candidate-table">
            <thead>
              <tr><th>Applicant ID</th><th>Name</th><th>Status</th><th>Guardrails Applied</th></tr>
            </thead>
            <tbody>
              {candidates.map(c => (
                <tr key={c.applicant_id}>
                  <td className="mono">{c.applicant_id}</td>
                  <td className="bold">{c.name}</td>
                  <td>
                    <span className={`status-badge-sm ${c.status.replace(/ /g, '-')}`}>
                      {c.status}
                    </span>
                  </td>
                  <td>
                    {c.guardrails.map((g, i) => {
                      const passed  = g.toLowerCase().includes('passed') || g.toLowerCase().includes('checked');
                      const blocked = g.toLowerCase().includes('blocked') || g.toLowerCase().includes('triggered');
                      return (
                        <div key={i} style={{ fontSize: '0.78rem', marginBottom: '3px', color: blocked ? '#991B1B' : passed ? '#065F46' : '#92400E' }}>
                          {blocked ? '&#128308;' : passed ? '&#128994;' : '&#128993;'} {g}
                        </div>
                      );
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

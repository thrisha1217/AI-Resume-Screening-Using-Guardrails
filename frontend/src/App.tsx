import { useState } from 'react';
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import ResultsPage from './pages/ResultsPage';
import { ScreeningResults } from './types';

type Page = 'home' | 'upload' | 'results';

export default function App() {
  const [page, setPage] = useState<Page>('home');
  const [results, setResults] = useState<ScreeningResults | null>(null);
  const [jobId, setJobId] = useState<string>('');

  return (
    <div className="app">
      <nav className="navbar">
        <div className="navbar-brand">
          <div className="navbar-icon">&#128269;</div>
          <div>
            <div className="navbar-title">Resume Screening System</div>
            <div className="navbar-sub">AI-Powered Candidate Evaluation</div>
          </div>
        </div>
        <div className="navbar-status">
          <span className="status-dot" />
          System Online
        </div>
      </nav>
      {page === 'home' && <HomePage onGetStarted={() => setPage('upload')} />}
      {page === 'upload' && (
        <UploadPage
          onResults={(r, jid) => { setResults(r); setJobId(jid); setPage('results'); }}
          onBack={() => setPage('home')}
        />
      )}
      {page === 'results' && results && (
        <ResultsPage
          results={results}
          jobId={jobId}
          onReset={() => { setPage('home'); setResults(null); setJobId(''); }}
        />
      )}
    </div>
  );
}

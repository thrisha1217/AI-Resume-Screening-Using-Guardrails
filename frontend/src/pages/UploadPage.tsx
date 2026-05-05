import { useState, useRef } from 'react';
import { submitScreening, getStatus, getResults } from '../api';
import { ScreeningResults } from '../types';

interface Props {
  onResults: (r: ScreeningResults, jobId: string) => void;
  onBack: () => void;
}

interface FileState { file: File | null; name: string; }

export default function UploadPage({ onResults, onBack }: Props) {
  const [req, setReq]     = useState<FileState>({ file: null, name: '' });
  const [excel, setExcel] = useState<FileState>({ file: null, name: '' });
  const [zip, setZip]     = useState<FileState>({ file: null, name: '' });
  const [loading, setLoading]   = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [error, setError]       = useState('');

  const reqRef   = useRef<HTMLInputElement>(null);
  const excelRef = useRef<HTMLInputElement>(null);
  const zipRef   = useRef<HTMLInputElement>(null);

  const allUploaded = req.file && excel.file && zip.file;

  const handleFile = (setter: (s: FileState) => void) =>
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) setter({ file: f, name: f.name });
    };

  const handleAnalyze = async () => {
    if (!req.file || !excel.file || !zip.file) return;
    setLoading(true); setError(''); setProgress(0);
    setStatusMsg('Submitting files...');
    try {
      const jobId = await submitScreening(req.file, excel.file, zip.file);
      setStatusMsg('Analyzing candidates...');
      await new Promise<void>((resolve, reject) => {
        const iv = setInterval(async () => {
          try {
            const s = await getStatus(jobId);
            setProgress(s.progress);
            if (s.log?.length) setStatusMsg(s.log[s.log.length - 1]);
            if (s.status === 'done') { clearInterval(iv); resolve(); }
            else if (s.status === 'error') { clearInterval(iv); reject(new Error(s.error || 'Failed')); }
          } catch (e) { clearInterval(iv); reject(e); }
        }, 1500);
      });
      setStatusMsg('Fetching results...');
      const results = await getResults(jobId);
      onResults(results, jobId);
    } catch (e: any) {
      setError(e.message || 'An error occurred');
      setLoading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-header">
        <button className="back-btn" onClick={onBack}>&#8592; Back</button>
        <div>
          <h2 className="upload-title">Upload Files</h2>
          <p className="upload-sub">Upload all three files to begin AI-powered screening</p>
        </div>
      </div>

      <div className="upload-grid">
        <div className={`upload-card ${req.file ? 'uploaded' : ''}`} onClick={() => reqRef.current?.click()}>
          <input ref={reqRef} type="file" accept=".pdf,.docx,.txt" hidden onChange={handleFile(setReq)} />
          <div className="upload-card-icon">&#128196;</div>
          <div className="upload-card-title">Requirements Document</div>
          <div className="upload-card-sub">PDF, DOCX, or TXT — job description with eligibility criteria</div>
          {req.file ? <div className="upload-card-file">&#10003; {req.name}</div>
                    : <div className="upload-card-btn">Browse Files</div>}
        </div>

        <div className={`upload-card ${excel.file ? 'uploaded' : ''}`} onClick={() => excelRef.current?.click()}>
          <input ref={excelRef} type="file" accept=".xlsx" hidden onChange={handleFile(setExcel)} />
          <div className="upload-card-icon">&#128202;</div>
          <div className="upload-card-title">Candidate Excel</div>
          <div className="upload-card-sub">XLSX — candidate data with degree, experience, skills</div>
          {excel.file ? <div className="upload-card-file">&#10003; {excel.name}</div>
                      : <div className="upload-card-btn">Browse Files</div>}
        </div>

        <div className={`upload-card ${zip.file ? 'uploaded' : ''}`} onClick={() => zipRef.current?.click()}>
          <input ref={zipRef} type="file" accept=".zip" hidden onChange={handleFile(setZip)} />
          <div className="upload-card-icon">&#128193;</div>
          <div className="upload-card-title">Resume Folder</div>
          <div className="upload-card-sub">ZIP — containing all candidate resume PDFs</div>
          {zip.file ? <div className="upload-card-file">&#10003; {zip.name}</div>
                    : <div className="upload-card-btn">Browse Files</div>}
        </div>
      </div>

      {error && <div className="error-box">&#10060; {error}</div>}

      {loading ? (
        <div className="progress-section">
          <div className="progress-label">{statusMsg}</div>
          <div className="progress-bar-wrap">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="progress-pct">{progress}%</div>
        </div>
      ) : (
        <div className="analyze-btn-wrap">
          {!allUploaded && (
            <div className="waiting-msg">
              Waiting for: {[!req.file && 'Requirements', !excel.file && 'Excel', !zip.file && 'Resume ZIP'].filter(Boolean).join(', ')}
            </div>
          )}
          <button className={`cta-btn ${!allUploaded ? 'disabled' : ''}`}
            onClick={handleAnalyze} disabled={!allUploaded}>
            &#128640;&nbsp;&nbsp;Start Screening
          </button>
        </div>
      )}
    </div>
  );
}

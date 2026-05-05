interface Props { onGetStarted: () => void; }

export default function HomePage({ onGetStarted }: Props) {
  return (
    <div className="home-page">
      <div className="hero">

        {/* Tag */}
        <div className="hero-center">
          <div className="hero-tag">&#9889; Automated AI Screening</div>
        </div>

        {/* Title */}
        <div className="hero-center">
          <h1 className="hero-title">
            Smart <span className="accent">Resume Screening</span>
            <br />Powered by AI
          </h1>
        </div>

        {/* Description */}
        <div className="hero-center">
          <p className="hero-desc">
            Upload your job requirements, candidate data, and resumes.
            The system automatically screens all candidates using eligibility
            rules, government checks, and semantic skill matching —
            then delivers a clean, downloadable report.
          </p>
        </div>

        {/* Feature Cards */}
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon">&#128203;</div>
            <div className="feature-title">6-Stage Screening</div>
            <div className="feature-desc">
              Degree &#8594; Specialisation &#8594; Percentage &#8594;
              Experience &#8594; Org Rules &#8594; Skill Match
            </div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">&#129302;</div>
            <div className="feature-title">AI-Powered</div>
            <div className="feature-desc">
              Llama 3.2 LLM extracts degrees from resumes and generates
              professional candidate introductions
            </div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">&#128737;</div>
            <div className="feature-title">Guardrails Safety</div>
            <div className="feature-desc">
              ToxicLanguage, NSFWText, and GuardrailsPII validators
              ensure safe, clean AI outputs
            </div>
          </div>
          <div className="feature-card">
            <div className="feature-icon">&#128202;</div>
            <div className="feature-title">Rich Output</div>
            <div className="feature-desc">
              Colour-coded Excel, candidate PDFs, AI introductions —
              all in one downloadable ZIP
            </div>
          </div>
        </div>

        {/* Steps */}
        <div className="hero-center">
          <div className="steps-row">
            {['Upload Requirements', 'Upload Candidate Excel', 'Upload Resume ZIP', 'View Results'].map((s, i) => (
              <div className="step-chip" key={i}>
                <div className="step-num">{i + 1}</div>
                <span>{s}</span>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Button — centered */}
        <div className="hero-center" style={{ marginTop: '2.5rem' }}>
          <button className="cta-btn" onClick={onGetStarted}>
            &#128269;&nbsp;&nbsp;Analyze Resumes
          </button>
        </div>

      </div>
    </div>
  );
}

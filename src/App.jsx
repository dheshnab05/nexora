
import React, { useMemo, useState } from 'react';
import {
  ShieldCheck,
  LayoutDashboard,
  FolderOpen,
  ClipboardList,
  BookOpen,
  Settings,
  Search,
  Bell,
  ChevronDown,
  ArrowUpRight,
  ArrowRight,
  Wallet,
  MailWarning,
  UserRound,
  MessageCircleWarning,
  FileText,
  CheckCircle2,
  CircleHelp,
  ExternalLink,
  Menu,
  X,
  ShieldAlert,
  ChevronRight,
  MoreHorizontal,
  Upload,
  Clock3,
  CircleAlert,
  ListChecks,
  LoaderCircle,
  FileCheck2,
  AlertCircle,
} from 'lucide-react';

function cleanComplaintDraft(value) {
  if (typeof value !== "string") return "";

  return value
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/^\s*---+\s*$/gm, "")
    .trim();
}

const API_URL = 'http://127.0.0.1:8000';

const PORTAL_URL = 'https://www.cybercrime.gov.in/';

const incidents = [
  {
    id: 'financial',
    icon: Wallet,
    title: 'Financial fraud',
    description: 'UPI, card, bank transfer or payment scam',
    tag: 'Urgent response',
    tone: 'red',
  },
  {
    id: 'phishing',
    icon: MailWarning,
    title: 'Phishing or scam message',
    description: 'Suspicious link, call, SMS or email',
    tag: 'Secure accounts',
    tone: 'orange',
  },
  {
    id: 'account',
    icon: UserRound,
    title: 'Account hacked',
    description: 'Email, social media or other online account',
    tag: 'Account recovery',
    tone: 'purple',
  },
  {
    id: 'harassment',
    icon: MessageCircleWarning,
    title: 'Online harassment',
    description: 'Threats, impersonation or abusive messages',
    tag: 'Preserve evidence',
    tone: 'blue',
  },
];

const journey = [
  {
    title: 'Describe what happened',
    detail: 'Record the incident type, date and key details.',
    icon: FileText,
  },
  {
    title: 'Collect the evidence',
    detail: 'Add relevant messages, screenshots or receipts.',
    icon: Upload,
  },
  {
    title: 'Check your case summary',
    detail: 'Review extracted details and fill any gaps.',
    icon: ListChecks,
  },
  {
    title: 'Follow the reporting steps',
    detail: 'Use the relevant official channel to report.',
    icon: ShieldCheck,
  },
];

const incidentTypeMap = {
  financial: 'Financial fraud / UPI fraud',
  phishing: 'Phishing or scam message',
  account: 'Account hacked',
  harassment: 'Online harassment',
};

export default function App() {
  const [incident, setIncident] = useState('');
  const [activeNav, setActiveNav] = useState('Overview');
  const [menuOpen, setMenuOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [notice, setNotice] = useState('');
  const [started, setStarted] = useState(false);

  const [completed, setCompleted] = useState([
    false,
    false,
    false,
    false,
  ]);

  // Module 1: Evidence processing
  const [evidenceFile, setEvidenceFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [processingError, setProcessingError] = useState('');
  const [processingResult, setProcessingResult] = useState(null);

  // Module 3: Guidance and complaint preparation
  const [incidentDate, setIncidentDate] = useState('');
  const [incidentDescription, setIncidentDescription] = useState('');
  const [incidentAmount, setIncidentAmount] = useState('');
  const [transactionId, setTransactionId] = useState('');
  const [contactNumber, setContactNumber] = useState('');
  const [contactEmail, setContactEmail] = useState('');

  const [draftResult, setDraftResult] = useState(null);
  const [checklistResult, setChecklistResult] = useState(null);
  const [guidanceLoading, setGuidanceLoading] = useState(false);
  const [guidanceError, setGuidanceError] = useState('');

  const selected = incidents.find((item) => item.id === incident);

  const progress = useMemo(
    () =>
      Math.round(
        (completed.filter(Boolean).length / journey.length) * 100
      ),
    [completed]
  );

  const navItems = [
    { label: 'Overview', icon: LayoutDashboard },
    { label: 'My incidents', icon: FolderOpen },
    { label: 'Action checklist', icon: ClipboardList },
    { label: 'Guidance library', icon: BookOpen },
  ];

  const visibleNav = navItems.filter((item) =>
    item.label.toLowerCase().includes(search.toLowerCase())
  );

  function beginPreparation() {
    if (!incident) {
      setNotice('Select an incident type first.');
      return;
    }

    setStarted(true);
    setNotice(`Preparation started for: ${selected.title}.`);

    setTimeout(() => {
      document.getElementById('evidence-section')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }, 100);
  }

  async function processEvidence() {
    if (!incident) {
      setProcessingError('Please select an incident type first.');
      return;
    }

    if (!evidenceFile) {
      setProcessingError('Please select an evidence file first.');
      return;
    }

    const allowedExtensions = [
      '.txt',
      '.csv',
      '.pdf',
      '.png',
      '.jpg',
      '.jpeg',
    ];

    const fileExtension = evidenceFile.name
      .slice(evidenceFile.name.lastIndexOf('.'))
      .toLowerCase();

    if (!allowedExtensions.includes(fileExtension)) {
      setProcessingError(
        'Unsupported file. Upload TXT, CSV, PDF, PNG, JPG or JPEG.'
      );
      return;
    }

    if (evidenceFile.size > 10 * 1024 * 1024) {
      setProcessingError(
        'The file exceeds the 10 MB limit. Choose a smaller file.'
      );
      return;
    }

    const formData = new FormData();
    formData.append('file', evidenceFile);
    formData.append('incident_type', incidentTypeMap[incident]);

    setProcessing(true);
    setProcessingError('');
    setProcessingResult(null);

    try {
      const response = await fetch(
        `${API_URL}/api/evidence/process`,
        {
          method: 'POST',
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || 'Evidence processing failed.'
        );
      }

      setProcessingResult(data);
    } catch (error) {
      setProcessingError(
        error.message ||
        'Could not connect to the backend. Check that FastAPI is running on port 8000.'
      );
    } finally {
      setProcessing(false);
    }
  }

  function resetEvidence() {
    setEvidenceFile(null);
    setProcessingResult(null);
    setProcessingError('');

    const input = document.getElementById('evidence-file');

    if (input) {
      input.value = '';
    }
  }

  async function prepareComplaint() {
    if (!incident || !incidentDescription.trim()) {
      setGuidanceError(
        'Select an incident type and enter an incident description.'
      );
      return;
    }

    setGuidanceLoading(true);
    setGuidanceError('');
    setDraftResult(null);
    setChecklistResult(null);

    try {
      const incidentType =
        incidentTypeMap[incident] || 'Other cybercrime';

      const [draftResponse, checklistResponse] = await Promise.all([
        fetch(`${API_URL}/api/guidance/complaint-draft-llm`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            incident_type: incidentType,
            incident_date: incidentDate,
            description: incidentDescription,
            amount: incidentAmount,
            transaction_id: transactionId,
            contact: contactNumber,
            email: contactEmail,
          }),
        }),

        fetch(
          `${API_URL}/api/guidance/checklist?incident_type=${encodeURIComponent(
            incidentType
          )}`
        ),
      ]);

      const draftData = await draftResponse.json();
      const checklistData = await checklistResponse.json();

      if (!draftResponse.ok) {
        throw new Error(
          draftData.detail || 'Could not generate the complaint draft.'
        );
      }

      if (
        !checklistResponse.ok ||
        checklistData.status === 'error'
      ) {
        throw new Error(
          checklistData.message ||
          'Could not load the incident checklist.'
        );
      }

      setDraftResult(draftData);
      setChecklistResult(checklistData);
    } catch (error) {
      setGuidanceError(
        error.message ||
        'Could not connect to the Nexora backend.'
      );
    } finally {
      setGuidanceLoading(false);
    }
  }

  async function copyComplaintDraft() {
    try {
      await navigator.clipboard.writeText(
        draftResult?.complaint_draft || ''
      );

      setNotice('Complaint draft copied. Review it before using it.');
    } catch {
      setGuidanceError(
        'Clipboard access was blocked. Select and copy the draft manually.'
      );
    }
  }

  const candidateFields =
    processingResult?.candidate_fields || {};

  const dataQuality =
    processingResult?.data_quality || {};

  const missingFields = dataQuality.missing_fields || [];

  const completeness =
    dataQuality.candidate_completeness_percent;

  return (
    <div className="app-shell">
      {menuOpen && (
        <button
          className="backdrop"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <aside
        className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}
      >
        <div className="brand-row">
          <div className="brand-icon">
            <ShieldCheck size={22} />
          </div>

          <div>
            <strong>Nexora</strong>
            <span>Cybercrime reporting guide</span>
          </div>

          <button
            className="mobile-close icon-btn"
            aria-label="Close navigation"
            onClick={() => setMenuOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <div className="nav-caption">WORKSPACE</div>

        <label className="search-box">
          <Search size={15} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Find a section"
          />
        </label>

        <nav className="navigation">
          {visibleNav.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={`nav-link ${activeNav === label ? 'active' : ''
                }`}
              onClick={() => {
                setActiveNav(label);
                setMenuOpen(false);
              }}
            >
              <Icon size={17} />
              <span>{label}</span>

              {label === 'My incidents' && (
                <span className="count">0</span>
              )}
            </button>
          ))}

          {!visibleNav.length && (
            <p className="no-results">No matching sections.</p>
          )}
        </nav>

        <div className="sidebar-bottom">
          <div className="help-box">
            <CircleHelp size={18} />

            <div>
              <strong>Need help?</strong>
              <p>
                Find official reporting links and practical safety
                advice.
              </p>

              <button
                onClick={() => setActiveNav('Guidance library')}
              >
                Open guidance <ArrowUpRight size={13} />
              </button>
            </div>
          </div>

          <button
            className={`nav-link settings-link ${activeNav === 'Settings' ? 'active' : ''
              }`}
            onClick={() => setActiveNav('Settings')}
          >
            <Settings size={17} />
            <span>Settings</span>
          </button>

          <div className="user-row">
            <div className="user-avatar">G</div>

            <div>
              <strong>Guest workspace</strong>
              <span>Local prototype</span>
            </div>

            <MoreHorizontal size={18} className="quiet" />
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button
            className="icon-btn mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={20} />
          </button>

          <div className="breadcrumbs">
            Workspace <ChevronRight size={14} />
            <strong>{activeNav}</strong>
          </div>

          <div className="top-actions">
            <span className="local-label">
              <span />
              Local demo
            </span>

            <button
              className="icon-btn bell"
              aria-label="Notifications"
              onClick={() =>
                setNotice('There are no new notifications.')
              }
            >
              <Bell size={17} />
            </button>

            <button
              className="account-btn"
              onClick={() =>
                setNotice('You are using the local guest prototype.')
              }
            >
              Guest <ChevronDown size={14} />
            </button>
          </div>
        </header>

        <div className="content">
          {activeNav !== 'Overview' && (
            <div className="section-message">
              <CircleHelp size={18} />

              <div>
                <strong>{activeNav}</strong>
                <p>
                  This section will be connected to the application
                  data as the modules are implemented.
                </p>
              </div>

              <button onClick={() => setActiveNav('Overview')}>
                Back to overview
              </button>
            </div>
          )}

          <section className="intro">
            <div className="breadcrumbs-label">
              CYBER INCIDENT SUPPORT
            </div>

            <h1>Know what to do next.</h1>

            <p>
              Get organised before reporting a cybercrime. Choose
              what happened, gather relevant evidence and follow the
              appropriate official steps.
            </p>
          </section>

          <section className="urgent-alert">
            <div className="alert-symbol">
              <ShieldAlert size={20} />
            </div>

            <div className="alert-text">
              <strong>Lost money to a cyber fraud?</strong>
              <p>
                Call <b>1930</b> immediately. Do not wait for this app
                to process your evidence.
              </p>
            </div>

            <a href={PORTAL_URL} target="_blank" rel="noreferrer">
              Report on official portal <ExternalLink size={14} />
            </a>
          </section>

          <section className="incident-section">
            <div className="section-title">
              <div>
                <span className="overline">GET STARTED</span>
                <h2>What happened?</h2>
                <p>
                  Choose the option that best describes your
                  situation.
                </p>
              </div>

              <span className="step-count">Step 1 of 4</span>
            </div>

            <div className="incident-list">
              {incidents.map(
                ({
                  id,
                  icon: Icon,
                  title,
                  description,
                  tag,
                  tone,
                }) => (
                  <button
                    key={id}
                    className={`incident-option ${incident === id ? 'chosen' : ''
                      }`}
                    onClick={() => {
                      setIncident(id);
                      setNotice('');
                      setProcessingError('');
                      setProcessingResult(null);
                      setGuidanceError('');
                      setDraftResult(null);
                      setChecklistResult(null);
                    }}
                    aria-pressed={incident === id}
                  >
                    <span className={`incident-symbol ${tone}`}>
                      <Icon size={20} />
                    </span>

                    <span className="incident-copy">
                      <strong>{title}</strong>
                      <small>{description}</small>
                      <em className={tone}>{tag}</em>
                    </span>

                    <span
                      className={`radio-dot ${incident === id ? 'checked' : ''
                        }`}
                    >
                      {incident === id && <span />}
                    </span>
                  </button>
                )
              )}
            </div>

            <div className="action-row">
              <span className="muted-note">
                <ShieldCheck size={15} />
                Your information stays in this demo unless you choose
                to share it.
              </span>

              <button
                className="primary-btn"
                onClick={beginPreparation}
              >
                Continue <ArrowRight size={16} />
              </button>
            </div>

            {notice && (
              <div className="notice" role="status">
                <CircleAlert size={16} />
                {notice}

                <button
                  aria-label="Dismiss message"
                  onClick={() => setNotice('')}
                >
                  <X size={14} />
                </button>
              </div>
            )}
          </section>

          {/* MODULE 1: DATA ENGINEERING */}
          {started && (
            <section
              className="panel evidence-panel"
              id="evidence-section"
            >
              <div className="panel-heading">
                <div>
                  <h2>Organise your evidence</h2>
                  <p>
                    Upload evidence to extract candidate details,
                    create a timeline and check for missing
                    information.
                  </p>
                  <p>
                    Selected incident:{' '}
                    <strong>{selected?.title}</strong>
                  </p>
                </div>

                <FileCheck2 size={24} />
              </div>

              <div className="evidence-upload">
                <Upload size={25} />

                <label htmlFor="evidence-file">
                  <strong>
                    {evidenceFile
                      ? evidenceFile.name
                      : 'Choose an evidence file'}
                  </strong>

                  <small>
                    TXT, CSV, PDF, PNG, JPG or JPEG · Maximum 10 MB
                  </small>
                </label>

                <input
                  id="evidence-file"
                  type="file"
                  accept=".txt,.csv,.pdf,.png,.jpg,.jpeg"
                  onChange={(event) => {
                    setEvidenceFile(event.target.files?.[0] || null);
                    setProcessingError('');
                    setProcessingResult(null);
                  }}
                />
              </div>

              <div className="action-row">
                <button
                  className="primary-btn"
                  onClick={processEvidence}
                  disabled={processing}
                >
                  {processing ? (
                    <>
                      <LoaderCircle size={16} />
                      Processing evidence...
                    </>
                  ) : (
                    <>
                      Process evidence <ArrowRight size={16} />
                    </>
                  )}
                </button>

                {(evidenceFile || processingResult) && (
                  <button
                    className="secondary-btn"
                    onClick={resetEvidence}
                    disabled={processing}
                  >
                    Clear evidence
                  </button>
                )}
              </div>

              {processingError && (
                <div className="processing-error" role="alert">
                  <AlertCircle size={17} />
                  <span>{processingError}</span>
                </div>
              )}

              {processingResult && (
                <div className="processing-results">
                  <div className="result-success">
                    <CheckCircle2 size={19} />

                    <div>
                      <strong>Evidence processed</strong>
                      <small>
                        Case ID:{' '}
                        {processingResult.case_id || 'Not provided'}
                      </small>
                    </div>
                  </div>

                  <div className="result-grid">
                    <div className="result-card">
                      <small>File</small>
                      <strong>
                        {processingResult.filename ||
                          evidenceFile?.name ||
                          'Uploaded file'}
                      </strong>
                    </div>

                    <div className="result-card">
                      <small>Processing status</small>
                      <strong>
                        {processingResult.processing_status ||
                          'Processed'}
                      </strong>
                    </div>

                    <div className="result-card">
                      <small>Completeness</small>
                      <strong>
                        {completeness !== undefined &&
                          completeness !== null
                          ? `${completeness}%`
                          : 'Not available'}
                      </strong>
                    </div>
                  </div>

                  <h3>Extracted information</h3>

                  {Object.keys(candidateFields).length > 0 ? (
                    <div className="extracted-fields">
                      {[
                        {
                          label: 'Incident dates',
                          values: candidateFields.dates,
                        },
                        {
                          label: 'Amounts found',
                          values: candidateFields.amounts,
                        },
                        {
                          label: 'Transaction references',
                          values:
                            candidateFields.transaction_references,
                        },
                        {
                          label: 'Phone numbers',
                          values: candidateFields.phone_numbers,
                        },
                        {
                          label: 'Email addresses',
                          values: candidateFields.email_addresses,
                        },
                      ]
                        .filter(
                          (field) =>
                            Array.isArray(field.values) &&
                            field.values.length > 0
                        )
                        .map((field) => (
                          <div
                            className="extracted-field"
                            key={field.label}
                          >
                            <span>{field.label}</span>

                            <div className="field-values">
                              {field.values.map((value, index) => (
                                <span
                                  className="field-value"
                                  key={`${value}-${index}`}
                                >
                                  {value}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <p>
                      No structured candidate fields were returned
                      by the backend.
                    </p>
                  )}

                  <h3>Missing information</h3>

                  {missingFields.length > 0 ? (
                    <ul>
                      {missingFields.map((field, index) => (
                        <li key={`${field}-${index}`}>
                          {String(field)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>
                      No missing required fields were reported by
                      the backend.
                    </p>
                  )}

                  {Array.isArray(processingResult.timeline) &&
                    processingResult.timeline.length > 0 && (
                      <>
                        <h3>Candidate incident timeline</h3>

                        <div className="timeline-results">
                          {processingResult.timeline.map(
                            (event, index) => (
                              <div
                                className="timeline-item"
                                key={`${event.date_candidate || 'event'}-${index}`}
                              >
                                <strong>
                                  {event.date_candidate ||
                                    'Date needs confirmation'}
                                </strong>

                                <p>
                                  {event.description ||
                                    'No description provided'}
                                </p>

                                <small>
                                  {event.verified
                                    ? 'Verified'
                                    : 'Needs verification'}
                                </small>
                              </div>
                            )
                          )}
                        </div>
                      </>
                    )}

                  <p className="verification-note">
                    Extracted values are candidates, not verified
                    facts. Check every value against the original
                    evidence before using it in a complaint.
                  </p>
                </div>
              )}
            </section>
          )}

          {/* MODULE 3: GUIDANCE AND COMPLAINT PREPARATION */}
          {started && selected && (
            <section
              className="panel evidence-panel guidance-panel"
              id="guidance-section"
            >
              <div className="panel-heading">
                <div>
                  <span className="overline">MODULE 3</span>
                  <h2>Guidance and complaint preparation</h2>
                  <p>
                    Organise incident details, retrieve relevant
                    guidance and prepare a draft for your review.
                  </p>
                </div>

                <BookOpen size={24} />
              </div>

              <div className="guidance-form">
                <label>
                  Incident date
                  <input
                    type="date"
                    value={incidentDate}
                    onChange={(event) =>
                      setIncidentDate(event.target.value)
                    }
                  />
                </label>

                <label>
                  Incident description *
                  <textarea
                    rows={4}
                    value={incidentDescription}
                    onChange={(event) =>
                      setIncidentDescription(event.target.value)
                    }
                    placeholder="Describe what happened. Do not include passwords, OTPs or PINs."
                  />
                </label>

                {incident === 'financial' && (
                  <>
                    <label>
                      Amount involved
                      <input
                        value={incidentAmount}
                        onChange={(event) =>
                          setIncidentAmount(event.target.value)
                        }
                        placeholder="e.g. INR 8000"
                      />
                    </label>

                    <label>
                      Transaction ID
                      <input
                        value={transactionId}
                        onChange={(event) =>
                          setTransactionId(event.target.value)
                        }
                        placeholder="Enter the reference if available"
                      />
                    </label>
                  </>
                )}

                <label>
                  Contact number (optional)
                  <input
                    value={contactNumber}
                    onChange={(event) =>
                      setContactNumber(event.target.value)
                    }
                    placeholder="Enter only if needed for your draft"
                  />
                </label>

                <label>
                  Email address (optional)
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(event) =>
                      setContactEmail(event.target.value)
                    }
                    placeholder="Enter only if needed for your draft"
                  />
                </label>

                <button
                  className="primary-btn"
                  onClick={prepareComplaint}
                  disabled={guidanceLoading}
                >
                  {guidanceLoading
                    ? 'Preparing guidance...'
                    : 'Generate complaint draft and checklist'}
                  <ArrowRight size={16} />
                </button>

                {guidanceError && (
                  <div className="processing-error" role="alert">
                    <AlertCircle size={17} />
                    <span>{guidanceError}</span>
                  </div>
                )}
              </div>

              {draftResult && (
                <div className="processing-results guidance-results">
                  <div className="result-success">
                    <CheckCircle2 size={19} />

                    <div>
                      <strong>Draft generated successfully</strong>
                      <small>
                        Review every detail before using it.
                      </small>
                    </div>
                  </div>

                  <h3>Complaint draft</h3>


                  <pre className="complaint-draft">
                    {cleanComplaintDraft(
                      typeof draftResult?.complaint_draft === "string"
                        ? draftResult.complaint_draft
                        : draftResult?.complaint_draft?.complaint_draft ?? ""
                    )}
                  </pre>

                  <button
                    className="secondary-btn"
                    onClick={copyComplaintDraft}
                  >
                    Copy complaint draft
                  </button>

                  <h3>Missing information</h3>

                  {draftResult.missing_fields?.length > 0 ? (
                    <ul>
                      {draftResult.missing_fields.map((field) => (
                        <li key={field}>{field}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>
                      No required fields are missing from the draft
                      form. Check optional fields too.
                    </p>
                  )}

                  <h3>Retrieved guidance and sources</h3>


                  {(draftResult.sources || draftResult.retrieved_guidance || []).length > 0 ? (
                    (draftResult.sources || draftResult.retrieved_guidance).map((source) => (
                      <p key={source.source_url}>
                        <a
                          href={source.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {source.source_name} <ExternalLink size={13} />
                        </a>
                      </p>
                    ))
                  ) : (
                    <p>
                      No matching guidance was retrieved. Check the knowledge base.
                    </p>
                  )}


                  <p className="verification-note">
                    This is a template-generated, unverified draft.
                    It has not been submitted to any authority.
                    Verify all details against your original
                    evidence.
                  </p>
                </div>
              )}

              {checklistResult && (
                <div className="processing-results guidance-results">
                  <h3>Recommended next steps</h3>

                  <ul>
                    {checklistResult.checklist.map((item, index) => (
                      <li key={`${index}-${item}`}>{item}</li>
                    ))}
                  </ul>

                  <a
                    href={checklistResult.official_portal}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open official cybercrime portal{' '}
                    <ExternalLink size={13} />
                  </a>
                </div>
              )}
            </section>
          )}

          {/* PROGRESS CHECKLIST */}
          <section
            className="dashboard-lower"
            id="case-progress"
          >
            <div className="panel progress-panel">
              <div className="panel-heading">
                <div>
                  <span className="overline">YOUR CHECKLIST</span>
                  <h2>Prepare to report</h2>
                </div>

                <strong className="progress-number">
                  {progress}% complete
                </strong>
              </div>

              <div className="progress-track">
                <span style={{ width: `${progress}%` }} />
              </div>

              <div className="task-list">
                {journey.map(
                  ({ title, detail, icon: Icon }, index) => (
                    <button
                      key={title}
                      className={`task-row ${completed[index] ? 'done' : ''
                        }`}
                      onClick={() =>
                        setCompleted((old) =>
                          old.map((value, i) =>
                            i === index ? !value : value
                          )
                        )
                      }
                    >
                      <span className="task-icon">
                        {completed[index] ? (
                          <CheckCircle2 size={18} />
                        ) : (
                          <Icon size={17} />
                        )}
                      </span>

                      <span className="task-copy">
                        <strong>{title}</strong>
                        <small>{detail}</small>
                      </span>

                      <span className="task-status">
                        {completed[index]
                          ? 'Done'
                          : started && index === 0
                            ? 'Start here'
                            : 'To do'}
                      </span>

                      <ChevronRight
                        size={16}
                        className="task-chevron"
                      />
                    </button>
                  )
                )}
              </div>

              {started && (
                <div className="started-note">
                  <CheckCircle2 size={16} />

                  <span>
                    <strong>{selected?.title} selected.</strong>{' '}
                    Upload and process evidence above to test the
                    Data Engineering module.
                  </span>
                </div>
              )}
            </div>

            <aside className="panel resource-panel">
              <div className="resource-heading">
                <BookOpen size={18} />
                <span>OFFICIAL RESOURCE</span>
              </div>

              <h2>Where to report</h2>

              <p>
                The National Cyber Crime Reporting Portal accepts
                cybercrime complaints. Review your information
                before submitting it through the official channel.
              </p>

              <a
                className="portal-link"
                href={PORTAL_URL}
                target="_blank"
                rel="noreferrer"
              >
                cybercrime.gov.in <ExternalLink size={14} />
              </a>

              <div className="resource-rule" />

              <div className="safety-tip">
                <ShieldCheck size={17} />
                <p>
                  Never share your OTP, UPI PIN or password with
                  anyone offering help.
                </p>
              </div>

              <div className="resource-foot">
                <span>
                  <Clock3 size={13} />
                  Guidance only
                </span>
                <span>Prototype v0.3</span>
              </div>
            </aside>
          </section>

          <footer className="footer">
            <span>Nexora · Student project prototype</span>

            <span>
              Official authorities handle complaint submission and
              investigation.
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}

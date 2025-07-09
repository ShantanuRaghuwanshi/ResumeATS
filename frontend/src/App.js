import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";
import Card from "./components/Card";
import Title from "./components/Title";
import Input from "./components/Input";
import TextArea from "./components/TextArea";
import Button from "./components/Button";
import Section from "./components/Section";
import Label from "./components/Label";
import Select from "./components/Select";
import DownloadLink from "./components/DownloadLink";
import ResumeSectionEditor from "./components/ResumeSectionEditor";

function SectionCard({ title, children }) {
  return (
    <div style={{
      background: "#fff",
      borderRadius: 20,
      boxShadow: "0 4px 24px 0 #e0e7ff",
      marginBottom: 32,
      padding: 32,
      minWidth: 340,
      maxWidth: 440,
      marginLeft: "auto",
      marginRight: 0,
      textAlign: "left",
      display: "flex",
      flexDirection: "column",
      gap: 10,
      border: "1.5px solid #c7d2fe"
    }}>
      <Label style={{ fontSize: 22, color: "#3730a3", marginBottom: 18, fontWeight: 700, letterSpacing: 0.5 }}>{title}</Label>
      {children}
    </div>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [parsed, setParsed] = useState(null);
  const [updated, setUpdated] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [filetype, setFiletype] = useState("docx");
  const [hovered, setHovered] = useState("");
  const [editing, setEditing] = useState(false);
  const [logs, setLogs] = useState([]);
  const [showLogs, setShowLogs] = useState(false);
  const [activeSection, setActiveSection] = useState("preview");

  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleUpload = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    const res = await axios.post("http://localhost:8000/upload_resume/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    setParsed(res.data);
  };

  const handleOptimize = async () => {
    if (!parsed || !jd) return;
    const formData = new FormData();
    formData.append("parsed", JSON.stringify(parsed));
    formData.append("jd", jd);
    const res = await axios.post("http://localhost:8000/optimize_resume/", formData);
    setUpdated(res.data);
  };

  const handleGenerate = async () => {
    if (!updated) return;
    const formData = new FormData();
    formData.append("parsed", JSON.stringify(updated));
    formData.append("template", "modern");
    formData.append("filetype", filetype);
    const res = await axios.post("http://localhost:8000/generate_resume/", formData);
    setDownloadUrl("http://localhost:8000" + res.data.download_url);
  };

  // PATCH resume sections
  const handleSectionChange = async (section, value) => {
    const res = await axios.patch("http://localhost:8000/resume_sections/", {
      [section]: value,
    });
    setParsed(res.data);
  };

  const fetchLogs = async () => {
    const res = await axios.get("http://localhost:8000/logs/");
    setLogs(res.data.logs || []);
  };

  useEffect(() => {
    if (showLogs) fetchLogs();
    // Optionally, poll logs every 2s when visible
    const interval = showLogs ? setInterval(fetchLogs, 2000) : null;
    return () => interval && clearInterval(interval);
  }, [showLogs]);

  // --- UI Layout ---
  // Navigation for single-page feel
  const navSections = [
    { key: "preview", label: "Preview" },
    { key: "personal", label: "Personal Details" },
    { key: "education", label: "Education" },
    { key: "work", label: "Work Experience" },
    { key: "projects", label: "Projects" },
    { key: "skills", label: "Skills" },
  ];

  return (
    <div className="resume-app-container">
      {/* Sidebar: Only upload and JD controls */}
      <div className="resume-sidebar">
        <Label>Upload Resume (PDF or DOCX)</Label>
        <label className="custom-file-upload">
          <input type="file" accept=".pdf,.docx" onChange={handleFileChange} />
          Choose File
        </label>
        <Button hovered={hovered} setHovered={setHovered} name="upload" onClick={handleUpload}>
          Upload & Parse
        </Button>
        <Label>Paste Job Description</Label>
        <TextArea
          rows={6}
          placeholder="Paste Job Description here..."
          value={jd}
          onChange={(e) => setJd(e.target.value)}
        />
        <Button hovered={hovered} setHovered={setHovered} name="optimize" onClick={handleOptimize}>
          Optimize Resume
        </Button>
      </div>
      {/* Main Resume Area: Everything else */}
      <div className="resume-main">
        <Title>Resume ATS System</Title>
        <nav className="resume-nav">
          {navSections.map((s) => (
            <button
              key={s.key}
              className={"resume-nav-btn" + (activeSection === s.key ? " active" : "")}
              onClick={() => setActiveSection(s.key)}
            >
              {s.label}
            </button>
          ))}
        </nav>
        {updated && (
          <>
            <Label>
              Download as:
              <Select value={filetype} onChange={e => setFiletype(e.target.value)}>
                <option value="docx">DOCX</option>
                <option value="pdf">PDF</option>
              </Select>
            </Label>
            <Button hovered={hovered} setHovered={setHovered} name="generate" onClick={handleGenerate}>
              Generate & Download
            </Button>
          </>
        )}
        {downloadUrl && (
          <DownloadLink href={downloadUrl}>Download Updated Resume</DownloadLink>
        )}
        <Button
          className="show-logs-btn"
          hovered={hovered}
          setHovered={setHovered}
          name="show-logs"
          onClick={() => setShowLogs((v) => !v)}
        >
          {showLogs ? "Hide Process Logs" : "Show Process Logs"}
        </Button>
        {showLogs && (
          <Section>
            <Label>Process Logs</Label>
            <pre style={{ background: "#222", color: "#fff", borderRadius: 8, padding: 12, fontSize: 13, maxHeight: 200, overflow: "auto" }}>{logs.join("\n")}</pre>
          </Section>
        )}
        {/* Section switching for single-page feel */}
        {activeSection === "preview" && (
          parsed && (
            <div className="resume-card-preview">
              <div className="resume-section-header">Personal Details</div>
              <div style={{ marginBottom: 10, fontSize: 17 }}>
                <b>Name:</b> <span style={{ color: "#3730a3" }}>{parsed.personal_details?.name || "-"}</span>
              </div>
              <div style={{ marginBottom: 10, fontSize: 17 }}>
                <b>Contact:</b> <span style={{ color: "#3730a3" }}>{parsed.personal_details?.contact || "-"}</span>
              </div>
              <div style={{ marginBottom: 10, fontSize: 17 }}>
                <b>LinkedIn:</b> <span style={{ color: "#3730a3" }}>{parsed.personal_details?.linkedin || "-"}</span>
              </div>
              <div className="resume-section-header">Education</div>
              {(parsed.education || []).length === 0 && <div style={{ color: "#64748b" }}>No education entries.</div>}
              {(parsed.education || []).map((edu, idx) => (
                <div key={idx} style={{ marginBottom: 18, padding: 12, borderRadius: 10, background: "#f1f5f9" }}>
                  <b style={{ color: "#3730a3" }}>{edu.degree}</b> @ <b>{edu.university}</b><br />
                  <span style={{ color: "#6366f1" }}>{edu.location}</span><br />
                  <span style={{ fontSize: 14, color: "#64748b" }}>From: {edu.from_year} To: {edu.to_year} {edu.gpa ? `| GPA: ${edu.gpa}` : ""}</span>
                </div>
              ))}
              <div className="resume-section-header">Work Experience</div>
              {(parsed.work_experience || []).length === 0 && <div style={{ color: "#64748b" }}>No work experience entries.</div>}
              {(parsed.work_experience || []).map((work, idx) => (
                <div key={idx} style={{ marginBottom: 22, padding: 12, borderRadius: 10, background: "#f1f5f9" }}>
                  <b style={{ color: "#3730a3" }}>{work.title}</b> @ <b>{work.company}</b><br />
                  <span style={{ color: "#6366f1" }}>{work.location}</span><br />
                  <span style={{ fontSize: 14, color: "#64748b" }}>From: {work.from_year} To: {work.to_year}</span><br />
                  {work.summary && <div style={{ margin: "8px 0", color: "#334155" }}>{work.summary}</div>}
                  {work.projects && work.projects.length > 0 && (
                    <div style={{ marginLeft: 12, marginTop: 6 }}>
                      <b style={{ color: "#3730a3" }}>Projects:</b>
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {work.projects.map((proj, pidx) => (
                          <li key={pidx}>
                            <b>{proj.name}</b>{proj.summary && <>: {proj.summary}</>}<br />
                            {proj.bullets && proj.bullets.length > 0 && (
                              <ul style={{ margin: 0, paddingLeft: 18 }}>
                                {proj.bullets.map((b, bidx) => <li key={bidx}>{b}</li>)}
                              </ul>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
              <div className="resume-section-header">Projects</div>
              {(parsed.projects || []).length === 0 && <div style={{ color: "#64748b" }}>No projects.</div>}
              {(parsed.projects || []).map((proj, idx) => (
                <div key={idx} style={{ marginBottom: 14, padding: 12, borderRadius: 10, background: "#f1f5f9" }}>
                  <b style={{ color: "#3730a3" }}>{proj.name}</b>
                  {proj.bullets && proj.bullets.length > 0 && (
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {proj.bullets.map((b, bidx) => <li key={bidx}>{b}</li>)}
                    </ul>
                  )}
                </div>
              ))}
              <div className="resume-section-header">Skills</div>
              {(parsed.skills || []).length === 0 && <div style={{ color: "#64748b" }}>No skills listed.</div>}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                {(parsed.skills || []).map((skill, idx) => (
                  <span key={idx} style={{ background: "#e0e7ff", color: "#3730a3", borderRadius: 8, padding: "8px 18px", fontWeight: 500, fontSize: 16 }}>{skill}</span>
                ))}
              </div>
            </div>
          )
        )}
        {/* Inline editors for each section */}
        {activeSection === "personal" && parsed && (
          <ResumeSectionEditor
            sectionKey="personal_details"
            sectionData={parsed.personal_details}
            onChange={val => handleSectionChange("personal_details", val)}
            title="Personal Details"
          />
        )}
        {activeSection === "education" && parsed && (
          <ResumeSectionEditor
            sectionKey="education"
            sectionData={parsed.education}
            onChange={val => handleSectionChange("education", val)}
            isList={true}
            itemFields={["university", "degree", "location", "from_year", "to_year", "gpa"]}
            title="Education"
          />
        )}
        {activeSection === "work" && parsed && (
          <ResumeSectionEditor
            sectionKey="work_experience"
            sectionData={parsed.work_experience}
            onChange={val => handleSectionChange("work_experience", val)}
            isList={true}
            itemFields={["title", "company", "location", "from_year", "to_year", "summary"]}
            title="Work Experience"
          />
        )}
        {activeSection === "projects" && parsed && (
          <ResumeSectionEditor
            sectionKey="projects"
            sectionData={parsed.projects}
            onChange={val => handleSectionChange("projects", val)}
            isList={true}
            itemFields={["name", "summary"]}
            title="Projects"
          />
        )}
        {activeSection === "skills" && parsed && (
          <ResumeSectionEditor
            sectionKey="skills"
            sectionData={parsed.skills}
            onChange={val => handleSectionChange("skills", val)}
            title="Skills"
          />
        )}
      </div>
    </div>
  );
}

export default App;

import React, { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [parsed, setParsed] = useState(null);
  const [updated, setUpdated] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [filetype, setFiletype] = useState("docx");

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

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

  return (
    <div style={{ maxWidth: 600, margin: "auto", padding: 20 }}>
      <h2>Resume ATS System</h2>
      <input type="file" accept=".pdf,.docx" onChange={handleFileChange} />
      <button onClick={handleUpload}>Upload & Parse</button>
      {parsed && (
        <>
          <h4>Parsed Resume:</h4>
          <pre>{JSON.stringify(parsed, null, 2)}</pre>
          <textarea
            rows={6}
            placeholder="Paste Job Description here..."
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            style={{ width: "100%" }}
          />
          <button onClick={handleOptimize}>Optimize Resume</button>
        </>
      )}
      {updated && (
        <>
          <h4>Updated Resume Data:</h4>
          <pre>{JSON.stringify(updated, null, 2)}</pre>
          <label>
            Download as:
            <select value={filetype} onChange={e => setFiletype(e.target.value)}>
              <option value="docx">DOCX</option>
              <option value="pdf">PDF</option>
            </select>
          </label>
          <button onClick={handleGenerate}>Generate & Download</button>
        </>
      )}
      {downloadUrl && (
        <a href={downloadUrl} download style={{ display: "block", marginTop: 20 }}>
          Download Updated Resume
        </a>
      )}
    </div>
  );
}

export default App;

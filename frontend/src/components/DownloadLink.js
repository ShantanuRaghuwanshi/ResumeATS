import React from "react";

const DownloadLink = ({ href, children }) => (
  <a
    href={href}
    download
    style={{
      display: "block",
      marginTop: 32,
      color: "#6366f1",
      fontWeight: 600,
      fontSize: 18,
      textDecoration: "none",
      background: "#e0e7ff",
      padding: "12px 24px",
      borderRadius: 12,
      boxShadow: "0 2px 8px 0 rgba(99, 102, 241, 0.08)",
      transition: "background 0.2s, color 0.2s"
    }}
  >
    {children}
  </a>
);

export default DownloadLink;

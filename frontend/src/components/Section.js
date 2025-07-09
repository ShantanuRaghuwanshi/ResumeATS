import React from "react";

const Section = ({ children }) => (
  <div style={{
    width: "100%",
    margin: "24px 0 0 0",
    background: "#f1f5f9",
    borderRadius: 16,
    padding: 20,
    boxShadow: "0 2px 8px 0 rgba(59, 130, 246, 0.05)"
  }}>
    {children}
  </div>
);

export default Section;

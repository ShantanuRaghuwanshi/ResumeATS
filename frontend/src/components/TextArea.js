import React from "react";

const TextArea = (props) => (
  <textarea
    style={{
      padding: "12px 16px",
      borderRadius: 12,
      border: "1px solid #c7d2fe",
      margin: "12px 0",
      width: "100%",
      fontSize: 16,
      background: "#fff",
      boxShadow: "0 2px 8px 0 rgba(59, 130, 246, 0.05)",
      transition: "border 0.2s",
      resize: "vertical",
      minHeight: 80,
      fontFamily: "inherit"
    }}
    {...props}
  />
);

export default TextArea;

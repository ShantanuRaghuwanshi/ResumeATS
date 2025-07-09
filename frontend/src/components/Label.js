import React from "react";

const Label = ({ children, ...props }) => (
  <label style={{ fontWeight: 500, color: "#6366f1", marginBottom: 8, display: "block", ...props.style }}>{children}</label>
);

export default Label;

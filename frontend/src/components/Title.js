import React from "react";

const Title = ({ children }) => (
  <h2 style={{
    fontSize: 32,
    fontWeight: 700,
    letterSpacing: 1,
    marginBottom: 16,
    color: "#3730a3",
    textShadow: "0 2px 8px #e0e7ff"
  }}>{children}</h2>
);

export default Title;

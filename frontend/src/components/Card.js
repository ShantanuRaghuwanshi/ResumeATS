import React from "react";

const Card = ({ children }) => (
  <div style={{
    background: "linear-gradient(135deg, #f8fafc 0%, #e0e7ff 100%)",
    boxShadow: "0 8px 32px 0 rgba(31, 38, 135, 0.15)",
    borderRadius: 24,
    padding: 32,
    margin: "40px auto",
    maxWidth: 600,
    minHeight: 600,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    position: "relative",
  }}>
    {children}
  </div>
);

export default Card;

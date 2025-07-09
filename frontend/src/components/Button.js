import React from "react";

const Button = ({ children, hovered, setHovered, name, ...props }) => {
  const base = {
    background: "linear-gradient(90deg, #6366f1 0%, #818cf8 100%)",
    color: "#fff",
    border: "none",
    borderRadius: 12,
    padding: "12px 28px",
    fontWeight: 600,
    fontSize: 16,
    margin: "16px 0 0 0",
    cursor: "pointer",
    boxShadow: "0 4px 16px 0 rgba(99, 102, 241, 0.15)",
    transition: "background 0.2s, transform 0.1s",
  };
  const hover = {
    background: "linear-gradient(90deg, #818cf8 0%, #6366f1 100%)",
    transform: "translateY(-2px) scale(1.03)",
  };
  return (
    <button
      style={hovered === name ? { ...base, ...hover } : base}
      onMouseEnter={() => setHovered(name)}
      onMouseLeave={() => setHovered("")}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;

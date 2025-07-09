import React from "react";

const Select = (props) => (
  <select
    style={{
      padding: "12px 16px",
      borderRadius: 12,
      border: "1px solid #c7d2fe",
      fontSize: 16,
      background: "#fff",
      marginLeft: 12,
      width: "auto",
      display: "inline-block"
    }}
    {...props}
  />
);

export default Select;

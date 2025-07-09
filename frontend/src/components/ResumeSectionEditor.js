import React from "react";
import Section from "./Section";
import Label from "./Label";
import Input from "./Input";
import TextArea from "./TextArea";
import Button from "./Button";

// Generic editor for a resume section (list or text)
export default function ResumeSectionEditor({
  sectionKey,
  sectionData,
  onChange,
  isList = false,
  itemFields = [],
  title,
}) {
  // For list sections (e.g., work_experience, projects)
  const handleItemChange = (idx, field, value) => {
    const updated = sectionData.map((item, i) =>
      i === idx ? { ...item, [field]: value } : item
    );
    onChange(updated);
  };
  const handleAddItem = () => {
    const empty = itemFields.reduce((acc, f) => ({ ...acc, [f]: "" }), {});
    onChange([...(sectionData || []), empty]);
  };
  const handleRemoveItem = (idx) => {
    onChange(sectionData.filter((_, i) => i !== idx));
  };

  if (isList) {
    return (
      <Section>
        <Label style={{ fontSize: 18 }}>{title}</Label>
        {(sectionData || []).map((item, idx) => (
          <div key={idx} style={{ marginBottom: 16, background: "#fff", borderRadius: 8, padding: 12, boxShadow: "0 1px 4px #e0e7ff" }}>
            {itemFields.map((field) => (
              <div key={field} style={{ marginBottom: 8 }}>
                <Label>{field.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</Label>
                <Input
                  value={item[field] || ""}
                  onChange={e => handleItemChange(idx, field, e.target.value)}
                />
              </div>
            ))}
            <Button name={`remove-${idx}`} hovered={null} setHovered={() => {}} style={{ background: "#f87171", color: "#fff", marginTop: 8 }} onClick={() => handleRemoveItem(idx)}>
              Remove
            </Button>
          </div>
        ))}
        <Button name="add" hovered={null} setHovered={() => {}} onClick={handleAddItem}>
          Add {title.slice(0, -1)}
        </Button>
      </Section>
    );
  }
  // For text or array sections (e.g., education, skills)
  return (
    <Section>
      <Label style={{ fontSize: 18 }}>{title}</Label>
      {Array.isArray(sectionData) ? (
        <TextArea
          value={sectionData.join(", ")}
          onChange={e => onChange(e.target.value.split(/,|\n/).map(s => s.trim()).filter(Boolean))}
        />
      ) : (
        <TextArea
          value={sectionData || ""}
          onChange={e => onChange(e.target.value)}
        />
      )}
    </Section>
  );
}

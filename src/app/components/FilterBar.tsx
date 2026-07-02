import { Search, FileSpreadsheet, Loader2, CheckCircle } from "lucide-react";
import { useState, useRef } from "react";

interface FilterBarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  riskFilter: string;
  onRiskFilterChange: (r: string) => void;
  termFilter: string;
  onTermFilterChange: (t: string) => void;
  subjectGroupCode?: string;
  onSubjectGroupCodeChange?: (s: string) => void;
  onImport: () => void;
}

const selectStyle: React.CSSProperties = {
  padding: "8px 32px 8px 12px",
  background: "#F9FAFB",
  border: "1px solid #E5E7EB",
  borderRadius: "8px",
  color: "#1A1A2E",
  fontSize: "13px",
  fontWeight: "500",
  outline: "none",
  cursor: "pointer",
  appearance: "none",
  WebkitAppearance: "none",
  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239CA3AF' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
  backgroundRepeat: "no-repeat",
  backgroundPosition: "right 10px center",
  minWidth: "160px",
};

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label style={{ color: "#6B7280", fontSize: "11px", fontWeight: "500", letterSpacing: "0.03em" }}>
      {children}
    </label>
  );
}

export function FilterBar({
  searchQuery,
  onSearchChange,
  riskFilter,
  onRiskFilterChange,
  termFilter,
  onTermFilterChange,
  subjectGroupCode = "All Classes",
  onSubjectGroupCodeChange = () => {},
  onImport,
}: FilterBarProps) {
  const [importing, setImporting] = useState(false);
  const [imported, setImported] = useState(false);
  const [fileName, setFileName] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setImporting(true);
    setImported(false);
    await new Promise((r) => setTimeout(r, 1800));
    setImporting(false);
    setImported(true);
    onImport();
    // Reset so the same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";
    setTimeout(() => setImported(false), 3000);
  };

  const handleClick = () => {
    if (!importing) fileInputRef.current?.click();
  };

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: "12px",
        padding: "16px 20px",
        boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
        display: "flex",
        alignItems: "flex-end",
        gap: "16px",
        flexWrap: "wrap",
      }}
    >
      {/* Term */}
      <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
        <FieldLabel>Term</FieldLabel>
        <select
          value={termFilter}
          onChange={(e) => onTermFilterChange(e.target.value)}
          style={selectStyle}
        >
          <option value="Semester 1 2026">Semester 1 2026</option>
          <option value="Semester 2 2025">Semester 2 2025</option>
          <option value="Semester 1 2025">Semester 1 2025</option>
          <option value="Semester 2 2024">Semester 2 2024</option>
        </select>
      </div>

      {/* Subject */}
      <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
        <FieldLabel>Subject</FieldLabel>
        <select style={{ ...selectStyle, minWidth: "160px" }}>
          <option>All Subjects</option>
          <option>BSYS301 – Business Systems</option>
          <option>BSYS201 – Data Analytics</option>
          <option>BSYS401 – Project Management</option>
          <option>INFO101 – Info Systems</option>
        </select>
      </div>

      {/* Risk Filter */}
      <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
        <FieldLabel>Risk Level</FieldLabel>
        <select
          value={riskFilter}
          onChange={(e) => onRiskFilterChange(e.target.value)}
          style={{ ...selectStyle, minWidth: "130px" }}
        >
          <option value="All">All Levels</option>
          <option value="HIGH">High Risk</option>
          <option value="MEDIUM">Medium Risk</option>
          <option value="LOW">Low Risk</option>
        </select>
      </div>

      {/* Divider */}
      <div style={{ width: "1px", height: "36px", background: "#E5E7EB", alignSelf: "flex-end" }} />

      {/* Subject Group Code */}
      <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
        <FieldLabel>Class Group</FieldLabel>
        <select
          value={subjectGroupCode}
          onChange={(e) => onSubjectGroupCodeChange(e.target.value)}
          style={{ ...selectStyle, minWidth: "180px" }}
        >
          <option value="All Classes">All Classes</option>
          <option value="ICT728LBT10126">ICT728LBT10126</option>
          <option value="BSYS301LBT10127">BSYS301LBT10127</option>
          <option value="BSYS201LBT10128">BSYS201LBT10128</option>
          <option value="INFO101LBT10129">INFO101LBT10129</option>
        </select>
      </div>

      {/* Search */}
      <div style={{ display: "flex", flexDirection: "column", gap: "5px", flex: 1, minWidth: "200px" }}>
        <FieldLabel>Search</FieldLabel>
        <div style={{ position: "relative" }}>
          <Search
            size={15}
            color="#9CA3AF"
            style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search students..."
            style={{
              width: "100%",
              padding: "8px 12px 8px 32px",
              background: "#F9FAFB",
              border: "1px solid #E5E7EB",
              borderRadius: "8px",
              color: "#1A1A2E",
              fontSize: "13px",
              outline: "none",
              boxSizing: "border-box",
              transition: "border-color 0.15s",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#185FA5")}
            onBlur={(e) => (e.target.style.borderColor = "#E5E7EB")}
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              style={{
                position: "absolute",
                right: "8px",
                top: "50%",
                transform: "translateY(-50%)",
                background: "#9CA3AF",
                border: "none",
                borderRadius: "50%",
                width: "16px",
                height: "16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                color: "#FFFFFF",
                fontSize: "10px",
                lineHeight: 1,
              }}
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Import Button */}
      <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
        <div style={{ height: "19px" }} />
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
        <button
          onClick={handleClick}
          disabled={importing}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 16px",
            background: imported ? "#ECFDF5" : importing ? "#EBF4FF" : "transparent",
            border: `1.5px solid ${imported ? "#22C55E" : "#185FA5"}`,
            borderRadius: "8px",
            cursor: importing ? "not-allowed" : "pointer",
            whiteSpace: "nowrap",
            opacity: importing ? 0.8 : 1,
            transition: "all 0.15s",
          }}
        >
          {importing ? (
            <Loader2 size={14} color="#185FA5" style={{ animation: "spin 1s linear infinite" }} />
          ) : imported ? (
            <CheckCircle size={14} color="#22C55E" />
          ) : (
            <FileSpreadsheet size={14} color="#185FA5" />
          )}
          <span style={{ color: imported ? "#16A34A" : "#185FA5", fontSize: "13px", fontWeight: "600" }}>
            {importing ? "Importing…" : imported ? "Imported!" : "Import Excel"}
          </span>
        </button>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
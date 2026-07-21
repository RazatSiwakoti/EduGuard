import type { StudentDetails } from "../api/students";

interface StudentDetailModalProps {
  student: StudentDetails | null;
  onClose: () => void;
}

export function StudentDetailModal({
  student,
  onClose,
}: StudentDetailModalProps) {
  if (!student) {
    return null;
  }

  const fullName = `${student.first_name} ${student.last_name}`;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(26,26,46,0.45)",
          zIndex: 100,
          backdropFilter: "blur(2px)",
        }}
      />

      {/* Modal */}
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: "520px",
          maxWidth: "calc(100vw - 32px)",
          background: "#FFFFFF",
          borderRadius: "16px",
          boxShadow: "0 24px 64px rgba(0,0,0,0.18)",
          zIndex: 101,
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "20px 24px",
            borderBottom: "1px solid #E5E7EB",
          }}
        >
          <div>
            <h2
              style={{
                margin: 0,
                color: "#1A1A2E",
                fontSize: "18px",
              }}
            >
              {fullName}
            </h2>

            <span
              style={{
                color: "#6B7280",
                fontSize: "12px",
              }}
            >
              {student.student_number}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close student details"
            style={{
              border: "none",
              background: "transparent",
              cursor: "pointer",
              fontSize: "18px",
            }}
          >
            ✕
          </button>
        </div>

        {/* Details */}
        <div
          style={{
            padding: "20px 24px",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "14px",
          }}
        >
          <Detail
            label="Status"
            value={student.status_description ?? "Not provided"}
          />

          <Detail
            label="Program"
            value={student.program ?? "Not provided"}
          />

          <Detail
            label="Email"
            value={student.email ?? "Not provided"}
          />

          <Detail
            label="Phone"
            value={student.phone ?? "Not provided"}
          />

          <Detail
            label="Age"
            value={student.age?.toString() ?? "Not provided"}
          />

          <Detail
            label="Gender"
            value={student.gender ?? "Not provided"}
          />

          <Detail
            label="Previously emailed"
            value={student.is_emailed ? "Yes" : "No"}
          />
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid #E5E7EB",
          }}
        >
          <button
            type="button"
            onClick={onClose}
            style={{
              width: "100%",
              padding: "10px",
              background: "#185FA5",
              color: "#FFFFFF",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              fontWeight: "600",
            }}
          >
            Close
          </button>
        </div>
      </div>
    </>
  );
}

interface DetailProps {
  label: string;
  value: string;
}

function Detail({ label, value }: DetailProps) {
  return (
    <div
      style={{
        background: "#F9FAFB",
        borderRadius: "8px",
        padding: "12px",
      }}
    >
      <div
        style={{
          color: "#9CA3AF",
          fontSize: "10px",
          textTransform: "uppercase",
          marginBottom: "4px",
        }}
      >
        {label}
      </div>

      <div
        style={{
          color: "#1A1A2E",
          fontSize: "13px",
          fontWeight: "600",
          overflowWrap: "anywhere",
        }}
      >
        {value}
      </div>
    </div>
  );
}
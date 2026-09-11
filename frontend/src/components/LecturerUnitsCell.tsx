import { useUnitsList } from "../hooks/useUnits";

interface LecturerUnitsCellProps {
  lecturerId: number;
}

// Shows the active units a given lecturer is currently teaching.
// Reuses the same useUnitsList query used by UnitsPanel — React Query
// dedupes identical concurrent requests, so even though every row in
// the Lecturers table calls this, it only triggers ONE network request,
// not one per lecturer.
export default function LecturerUnitsCell({
  lecturerId,
}: LecturerUnitsCellProps) {
  const { data: units, isLoading } = useUnitsList(false);

  if (isLoading) {
    return <span className="text-xs text-stone-400">…</span>;
  }

  const teaching = units?.filter((u) => u.lecturer_id === lecturerId) ?? [];

  if (teaching.length === 0) {
    return <span className="text-xs text-stone-400">—</span>;
  }

  return (
    <div className="flex flex-col gap-0.5">
      {teaching.map((u) => (
        <span key={u.id} className="text-xs text-stone-600">
          {u.unit_code} · {u.unit_name}
          {u.year ? ` · ${u.year}` : ""}
          {u.teaching_period ? ` · ${u.teaching_period}` : ""}
          {u.level ? ` · ${u.level}` : ""}
        </span>
      ))}
    </div>
  );
}
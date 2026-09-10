import { useQuery } from "@tanstack/react-query";
import { studentDetailService } from "../services/studentDetailService";

export interface TrajectoryRow {
  checkpoint_week: number;
  rule_tier: string | null;
  ml_tier: string | null;
  final_tier: string | null;
  requires_review: boolean;
  attendance_pct: number | null;
  tutorial_pct: number | null;
  assessment_avg: number | null;
}

export function useStudentTrajectory(studentId: number, unitId: number) {
  return useQuery<TrajectoryRow[]>({
    queryKey: ["student-trajectory", studentId, unitId],
    queryFn: () => studentDetailService.trajectory(studentId, unitId),
    staleTime: 60_000,
  });
}
